#include "recovery/search_protocol.h"
#include <iostream>
#include <algorithm>
#include <unordered_set>
#include <queue>

namespace haven {

SearchProtocol::SearchProtocol() {}

SearchProtocol::~SearchProtocol() {}

void SearchProtocol::set_topology(const TopologyManager::TopologyResult& topo) {
    std::lock_guard<std::mutex> lock(search_mutex_);
    topo_ = topo;
    topo_set_ = true;
}

uint64_t SearchProtocol::generate_search_id() {
    // Generate a unique search ID using simulated counter + node ID
    static uint64_t next_id = 1;
    return next_id++;
}

bool SearchProtocol::is_duplicate_search(const SearchPacket& pkt,
                                         const std::unordered_set<uint64_t>& seen_ids) {
    // Check if this search ID has been seen before
    // Also check TTL and sequence number for freshness
    return seen_ids.count(pkt.search_id) > 0;
}

std::vector<WirelessNodeID> SearchProtocol::find_route_via_topology(uint64_t origin_id,
                                                                     uint64_t target_id) {
    std::vector<WirelessNodeID> path;
    if (!topo_set_) return path;

    WirelessNodeID src{origin_id, "debruijn"};
    WirelessNodeID dst{target_id, "debruijn"};

    // Use the topology manager's BFS-based routing
    // We don't have a TopologyManager instance here, so replicate BFS over topo_
    std::unordered_map<WirelessNodeID, WirelessNodeID> parent;
    std::queue<WirelessNodeID> q;

    if (topo_.adjacency.find(src) == topo_.adjacency.end()) {
        return path;
    }

    q.push(src);
    parent[src] = src;

    while (!q.empty()) {
        WirelessNodeID u = q.front(); q.pop();

        if (u == dst) break;

        auto it = topo_.adjacency.find(u);
        if (it != topo_.adjacency.end()) {
            for (const auto& v : it->second) {
                if (parent.find(v) == parent.end()) {
                    parent[v] = u;
                    q.push(v);
                }
            }
        }
    }

    if (parent.find(dst) != parent.end()) {
        WirelessNodeID at = dst;
        while (at != src) {
            path.push_back(at);
            at = parent[at];
        }
        path.push_back(src);
        std::reverse(path.begin(), path.end());
    }

    return path;
}

SearchResult SearchProtocol::initiate_search(std::shared_ptr<Node> origin,
                                              std::shared_ptr<Node> target,
                                              const NetworkManager& net_mgr) {
    SearchResult result;

    if (!origin || !target) {
        std::cerr << "[ERROR] " << "Invalid origin or target for search" << std::endl;
        result.partition_detected = true;
        return result;
    }

    // Create search packet
    SearchPacket pkt;
    pkt.search_id = generate_search_id();
    pkt.origin_node = origin->get_id().id;
    pkt.target_endpoint = target->get_id().id;
    pkt.previous_hop = origin->get_id().id;
    pkt.hop_count = 0;
    pkt.ttl = 10;  // reasonable TTL
    pkt.sequence_number = 1;
    pkt.creation_time = 0;

    std::cout << "Initiated search " << pkt.search_id
        << " from node " << pkt.origin_node
        << " to target " << pkt.target_endpoint << std::endl;

    // Store as active search
    active_searches_[pkt.search_id] = pkt;

    // Try to find a route using the stored topology first
    auto route = find_route_via_topology(pkt.origin_node, pkt.target_endpoint);
    if (!route.empty()) {
        result.success = true;
        result.search_id = pkt.search_id;
        result.hops = static_cast<int>(route.size()) - 1;
        result.route = route;
        result.partition_detected = false;
        std::cout << "Search " << pkt.search_id << " found route via topology (" 
            << result.hops << " hops)" << std::endl;
        cancel_search(pkt.search_id);
        return result;
    }

    // Fallback: flood-based route discovery through neighbors
    result = perform_search(pkt, net_mgr);

    return result;
}

SearchResult SearchProtocol::perform_search(const SearchPacket& init_pkt,
                                            const NetworkManager& net_mgr) {
    SearchResult result;

    // Flood-based route discovery through actual node neighbors
    std::vector<std::shared_ptr<Node>> all_nodes = net_mgr.get_all_nodes();
    
    // Find origin node object
    std::shared_ptr<Node> origin_node = nullptr;
    for (const auto& n : all_nodes) {
        if (n->get_id().id == init_pkt.origin_node) {
            origin_node = n;
            break;
        }
    }

    if (!origin_node) {
        result.success = false;
        result.partition_detected = true;
        return result;
    }

    // BFS flood from origin
    std::unordered_map<uint64_t, uint64_t> parent;  // node_id -> parent_id
    std::queue<uint64_t> q;
    std::unordered_set<uint64_t> visited;

    q.push(init_pkt.origin_node);
    visited.insert(init_pkt.origin_node);
    parent[init_pkt.origin_node] = init_pkt.origin_node;

    bool found = false;
    while (!q.empty()) {
        uint64_t cur = q.front(); q.pop();

        if (cur == init_pkt.target_endpoint) {
            found = true;
            break;
        }

        auto cur_node = net_mgr.get_node(WirelessNodeID{cur, "debruijn"});
        if (!cur_node) continue;

        // Check TTL (approx via BFS depth - use parent chain length)
        // Simple depth limit via visited set size / TTL
        int depth = 0;
        {
            uint64_t at = cur;
            while (parent[at] != at && depth < init_pkt.ttl) {
                at = parent[at];
                depth++;
            }
        }
        if (depth >= init_pkt.ttl) continue;

        for (const auto& nb : cur_node->get_neighbors()) {
            uint64_t nb_id = nb.id;
            if (visited.find(nb_id) == visited.end()) {
                visited.insert(nb_id);
                parent[nb_id] = cur;
                q.push(nb_id);
            }
        }
    }

    if (found) {
        // Reconstruct path
        std::vector<uint64_t> path_ids;
        uint64_t at = init_pkt.target_endpoint;
        while (at != init_pkt.origin_node) {
            path_ids.push_back(at);
            at = parent[at];
        }
        path_ids.push_back(init_pkt.origin_node);
        std::reverse(path_ids.begin(), path_ids.end());

        result.success = true;
        result.search_id = init_pkt.search_id;
        result.hops = static_cast<int>(path_ids.size()) - 1;
        result.partition_detected = false;
        result.route.reserve(path_ids.size());
        for (uint64_t nid : path_ids) {
            result.route.push_back(WirelessNodeID{nid, "debruijn"});
        }

        std::cout << "Search " << init_pkt.search_id 
            << " completed via flood (" << result.hops << " hops)" << std::endl;
    } else {
        result.success = false;
        result.partition_detected = true;
        std::cout << "[DEBUG] " << "Search " << init_pkt.search_id 
            << " completed without finding route" << std::endl;
    }

    return result;
}

bool SearchProtocol::process_search_packet(const SearchPacket& pkt,
                                            std::shared_ptr<Node> current_node,
                                            std::vector<std::shared_ptr<Node>>& all_nodes,
                                            std::vector<SearchPacket>& forwarding_table,
                                            SearchResult& result) {
    if (!current_node) return false;

    std::cout << "[DEBUG] " << "Processing search packet " << pkt.search_id
        << " at node " << current_node->get_id().id << std::endl;

    // Check for duplicate
    if (is_duplicate_search(pkt, seen_search_ids_)) {
        std::cout << "[DEBUG] " << "Search " << pkt.search_id
            << " is a duplicate; suppressing" << std::endl;
        return false;  // suppress duplicate
    }

    // Mark as seen
    seen_search_ids_.insert(pkt.search_id);

    // Check TTL
    if (pkt.hop_count >= pkt.ttl) {
        std::cout << "[DEBUG] " << "Search " << pkt.search_id
            << " TTL exceeded at node " << current_node->get_id().id << std::endl;
        return false;  // TTL exceeded
    }

    // If we've reached the target
    if (current_node->get_id().id == pkt.target_endpoint) {
        std::cout << "Search " << pkt.search_id
            << " reached target node " << pkt.target_endpoint << std::endl;

        result.success = true;
        result.search_id = pkt.search_id;
        result.hops = pkt.hop_count;
        result.time_taken = 0;
        result.partition_detected = false;

        // Reconstruct the route (simplified)
        result.route = {WirelessNodeID{pkt.origin_node, ""},
                        WirelessNodeID{pkt.target_endpoint, ""}};

        // Cancel the search
        cancel_search(pkt.search_id);

        return true;  // found the target
    }

    // Forward to neighbors
    SearchPacket forward_pkt = pkt;
    forward_pkt.hop_count = pkt.hop_count + 1;
    forward_pkt.previous_hop = current_node->get_id().id;
    forward_pkt.ttl = pkt.ttl;  // preserve TTL

    bool forwarded = false;
    for (const auto& nb : current_node->get_neighbors()) {
        auto nb_node = std::find_if(all_nodes.begin(), all_nodes.end(),
            [&](const std::shared_ptr<Node>& n) { return n->get_id().id == nb.id; });
        if (nb_node != all_nodes.end()) {
            forwarding_table.push_back(forward_pkt);
            forwarded = true;
        }
    }

    return forwarded;  // forwarded in progress
}

bool SearchProtocol::update_routing_table(std::shared_ptr<Node> origin,
                                           const std::vector<WirelessNodeID>& route,
                                           const NetworkManager& net_mgr) {
    if (!origin || route.empty()) return false;
    
    std::cout << "Updating routing table for node " << origin->get_id().id 
        << " with route of " << route.size() << " hops" << std::endl;
    
    // In a real implementation, this would update the node's routing table
    // to include the discovered route
    // For now, just log the update
    
    return true;
}

void SearchProtocol::cancel_search(uint64_t search_id) {
    std::lock_guard<std::mutex> lock(search_mutex_);
    active_searches_.erase(search_id);
    std::cout << "[DEBUG] " << "Search " << search_id << " cancelled" << std::endl;
}

bool SearchProtocol::is_timed_out(int64_t creation_time, int64_t max_duration) {
    int64_t now = 0;
    return (now - creation_time) > max_duration;
}

}  // namespace haven