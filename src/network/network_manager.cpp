#include "network/network_manager.h"
#include <iostream>
#include <cmath>

namespace haven {

NetworkManager::NetworkManager()
    : node_limit_(std::numeric_limits<size_t>::max()),
      simulation_time_(0)
{
}

NetworkManager::~NetworkManager() {}

std::shared_ptr<Node> NetworkManager::add_node(WirelessNodeID id, NodePosition position, double battery) {
    std::lock_guard<std::mutex> lock(nodes_mutex_);
    
    // Check limit
    if (nodes_.size() >= node_limit_) {
        std::cout << "[WARN] " << "Node limit reached: cannot add node " << id.id << std::endl;
        return nullptr;
    }
    
    // Check for duplicate ID
    if (nodes_.count(id) > 0) {
        std::cout << "[WARN] " << "Duplicate node ID: " << id.id << std::endl;
        return nullptr;
    }
    
    auto node = std::make_shared<Node>(id, position, battery);
    nodes_[id] = node;
    node->set_join_time(simulation_time_);
    
    std::cout << "Added node " << id.id << " with battery " << battery << std::endl;
    return node;
}

void NetworkManager::remove_node(WirelessNodeID id) {
    std::lock_guard<std::mutex> lock(nodes_mutex_);
    
    auto it = nodes_.find(id);
    if (it != nodes_.end()) {
        // Remove all links to this node
        for (auto& pair : nodes_) {
            pair.second->set_link_to(id, false);
        }
        link_status_.erase(id);
        
        nodes_.erase(it);
        std::cout << "Removed node " << id.id << std::endl;
    }
}

std::shared_ptr<Node> NetworkManager::get_node(WirelessNodeID id) const {
    auto it = nodes_.find(id);
    if (it != nodes_.end()) {
        return it->second;
    }
    return nullptr;
}

std::vector<std::shared_ptr<Node>> NetworkManager::get_all_nodes() const {
    std::lock_guard<std::mutex> lock(nodes_mutex_);
    std::vector<std::shared_ptr<Node>> result;
    for (const auto& pair : nodes_) {
        result.push_back(pair.second);
    }
    return result;
}

void NetworkManager::discover_neighbors(std::shared_ptr<Node> node) {
    std::lock_guard<std::mutex> lock(nodes_mutex_);
    
    perform_neighbor_discovery(node);
}

void NetworkManager::update_neighbor_list(std::shared_ptr<Node> node) {
    std::lock_guard<std::mutex> lock(nodes_mutex_);
    perform_neighbor_discovery(node);
}

bool NetworkManager::node_join_request(std::shared_ptr<Node> new_node, std::shared_ptr<Node> joining_node) {
    // Basic check: new node must authenticate the joining node
    // This is a placeholder - full auth handshake happens elsewhere
    
    if (!new_node || !joining_node) {
        return false;
    }
    
    // Discover neighbors of the new node
    discover_neighbors(joining_node);
    
    // TODO: Full authentication handshake
    // For now, mark as joining and return success
    joining_node->set_auth_status(AuthStatus::AUTHENTICATING);
    
    std::cout << "Join request from node " << joining_node->get_id().id << " to " << new_node->get_id().id << std::endl;
    return true;
}

bool NetworkManager::node_leave(std::shared_ptr<Node> leaving_node) {
    if (!leaving_node) return false;
    
    WirelessNodeID id = leaving_node->get_id();
    node_leave_internal(leaving_node);
    return true;
}

void NetworkManager::node_leave_internal(std::shared_ptr<Node> leaving_node) {
    std::lock_guard<std::mutex> lock(nodes_mutex_);
    
    WirelessNodeID id = leaving_node->get_id();
    
    // Disconnect all links
    for (auto& pair : nodes_) {
        if (pair.first != id) {
            pair.second->set_link_to(id, false);
        }
    }
    link_status_.erase(id);
    
    // Remove from nodes map (but don't delete - may rejoin)
    nodes_.erase(id);
    
    std::cout << "Node " << id.id << " left the network" << std::endl;
}

void NetworkManager::node_fail(std::shared_ptr<Node> failing_node) {
    if (!failing_node) return;
    
    std::lock_guard<std::mutex> lock(nodes_mutex_);
    
    WirelessNodeID id = failing_node->get_id();
    nodes_[id]->set_status(NodeStatus::FAILED);
    
    // Disconnect all links
    for (auto& pair : nodes_) {
        pair.second->set_link_to(id, false);
    }
    link_status_.erase(id);
    
    std::cout << "Node " << id.id << " failed" << std::endl;
}

void NetworkManager::node_recover(std::shared_ptr<Node> recovering_node) {
    if (!recovering_node) return;
    
    std::lock_guard<std::mutex> lock(nodes_mutex_);
    
    WirelessNodeID id = recovering_node->get_id();
    nodes_[id]->set_status(NodeStatus::ACTIVE);
    nodes_[id]->set_residual_battery(
        std::min(nodes_[id]->get_residual_battery() + 10.0, nodes_[id]->get_battery_capacity()));
    
    // Re-establish links within range
    for (auto& pair : nodes_) {
        if (pair.first != id) {
            double dist = pair.second->get_position().distance_to(recovering_node->get_position());
            if (dist <= /* wireless_range */ 200.0) {
                pair.second->set_link_to(id, true);
                nodes_[id]->add_neighbor(pair.first, simulation_time_);
            }
        }
    }
    
    std::cout << "Node " << id.id << " recovered" << std::endl;
}

void NetworkManager::establish_link(std::shared_ptr<Node> a, std::shared_ptr<Node> b) {
    if (!a || !b) return;
    
    WirelessNodeID id_a = a->get_id();
    WirelessNodeID id_b = b->get_id();
    
    // Physical range check
    double dist = a->get_position().distance_to(b->get_position());
    // NS-3 range check would be more accurate
    
    a->add_neighbor(id_b, simulation_time_);
    b->add_neighbor(id_a, simulation_time_);
    
    a->set_link_to(id_b, true);
    b->set_link_to(id_a, true);
    
    std::cout << "Established link between " << id_a.id << " and " << id_b.id << std::endl;
}

void NetworkManager::disconnect_link(std::shared_ptr<Node> a, std::shared_ptr<Node> b) {
    if (!a || !b) return;
    
    WirelessNodeID id_a = a->get_id();
    WirelessNodeID id_b = b->get_id();
    
    a->remove_neighbor(id_b);
    b->remove_neighbor(id_a);
    
    a->set_link_to(id_b, false);
    b->set_link_to(id_a, false);
    
    std::cout << "Disconnected link between " << id_a.id << " and " << id_b.id << std::endl;
}

bool NetworkManager::link_exists(std::shared_ptr<Node> a, std::shared_ptr<Node> b) const {
    if (!a || !b) return false;
    return a->has_link_to(b->get_id());
}

void NetworkManager::assign_cluster(std::shared_ptr<Node> node, uint32_t cluster_id) {
    if (!node) return;
    node->set_cluster_id(cluster_id);
}

void NetworkManager::elect_cluster_head(std::shared_ptr<Node> candidate) {
    if (!candidate) return;
    
    // Reset previous cluster head if needed
    // TODO: Implement proper HEED clustering
    
    candidate->set_cluster_head(true);
    std::cout << "Elected cluster head: " << candidate->get_id().id << std::endl;
}

bool NetworkManager::authenticate_node(std::shared_ptr<Node> node) {
    if (!node) return false;
    
    // Placeholder: mark as authenticated for now
    // Full mutual authentication uses the three-message handshake
    node->set_auth_status(AuthStatus::AUTHENTICATED);
    std::cout << "Node " << node->get_id().id << " authenticated" << std::endl;
    return true;
}

void NetworkManager::reject_node(std::shared_ptr<Node> node) {
    if (!node) return;
    node->set_auth_status(AuthStatus::REVOKED);
    std::cout << "Node " << node->get_id().id << " rejected" << std::endl;
}

void NetworkManager::start_leader_election(std::shared_ptr<Node> initiator) {
    if (!initiator) return;
    
    initiator->set_epoch(simulation_time_);
    initiator->set_election_score(
        calculate_election_score(initiator)
    );
    
    std::cout << "Started leader election by node " << initiator->get_id().id << std::endl;
    // TODO: Propagate candidate info, max-consensus, etc.
}

int64_t NetworkManager::calculate_election_score(std::shared_ptr<Node> node) {
    if (!node) return 0;
    // Simple score: combine residual battery and stability
    int64_t score = static_cast<int64_t>(node->get_residual_battery() * 100);
    if (node->is_leader()) score += 1000;
    if (node->is_cluster_head()) score += 500;
    return score;
}

std::shared_ptr<Node> NetworkManager::get_current_leader() const {
    for (const auto& pair : nodes_) {
        if (pair.second->is_leader()) {
            return pair.second;
        }
    }
    return nullptr;
}

void NetworkManager::update_leader(std::shared_ptr<Node> new_leader) {
    if (!new_leader) return;
    
    // Reset previous leader
    for (auto& pair : nodes_) {
        pair.second->set_leader(false);
    }
    
    // Set new leader
    new_leader->set_leader(true);
    
    std::cout << "New leader elected: " << new_leader->get_id().id << std::endl;
}

void NetworkManager::trigger_neighbor_discovery() {
    // Discover neighbors for all nodes
    for (auto& pair : nodes_) {
        perform_neighbor_discovery(pair.second);
    }
}

void NetworkManager::discharge_node(std::shared_ptr<Node> node, double energy) {
    if (!node) return;
    node->set_residual_battery(
        std::max(0.0, node->get_residual_battery() - energy)
    );
}

void NetworkManager::recharge_node(std::shared_ptr<Node> node, double energy) {
    if (!node) return;
    node->set_residual_battery(
        std::min(node->get_battery_capacity(), node->get_residual_battery() + energy)
    );
}

size_t NetworkManager::get_node_limit() const { return node_limit_; }

void NetworkManager::set_node_limit(size_t limit) { node_limit_ = limit; }

int64_t NetworkManager::get_simulation_time() const { return simulation_time_; }

void NetworkManager::set_simulation_time(int64_t time) { simulation_time_ = time; }

bool NetworkManager::within_wireless_range(std::shared_ptr<Node> a, std::shared_ptr<Node> b) const {
    double dist = a->get_position().distance_to(b->get_position());
    return dist <= /* wireless_range */ 200.0;
}

void NetworkManager::perform_neighbor_discovery(std::shared_ptr<Node> node) {
    if (!node) return;
    
    std::vector<NeighborInfo> visible;
    
    for (const auto& pair : nodes_) {
        const auto& other = pair.second;
        if (other.get() == node.get()) continue;
        if (other->get_status() != NodeStatus::ACTIVE) continue;
        
        double dist = node->get_position().distance_to(other->get_position());
        double range = 200.0;  // from config
        
        if (dist <= range) {
            NeighborInfo info;
            info.id = other->get_id();
            info.position = other->get_position();
            info.last_seen = simulation_time_;
            info.signal_strength = 1.0 - (dist / range);  // simple RSSI model
            info.valid = true;
            visible.push_back(info);
        }
    }
    
    // Store visible neighbors (replace existing)
    // In a full implementation, we'd merge with existing neighbors
    node->set_last_seen(simulation_time_);
    
    std::cout << "[DEBUG] " << "Node " << node->get_id().id << " discovered " << visible.size() << " neighbors" << std::endl;
}

}  // namespace haven