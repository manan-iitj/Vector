#include "clustering/heed.h"
#include <iostream>
#include <cmath>
#include <algorithm>
#include <numeric>

namespace haven {

HEED::HEED() {}

HEED::~HEED() {}

void HEED::set_params(const HEEDParams& params) {
    params_ = params;
}

HEEDParams HEED::get_params() const {
    return params_;
}

std::vector<ClusterInfo> HEED::run_clustering(
    const std::vector<std::shared_ptr<Node>>& nodes,
    const NetworkManager& net_mgr) {
    
    std::cout << "Running HEED clustering on " << nodes.size() << " nodes" << std::endl;
    
    if (nodes.empty()) {
        std::cout << "[WARN] " << "No nodes for clustering" << std::endl;
        return {};
    }
    
    double wireless_range = 200.0;  // from config
    
    // Step 1: Select cluster heads
    std::vector<uint64_t> cluster_heads = select_cluster_heads(nodes, wireless_range);
    
    std::cout << "[DEBUG] " << "Selected " << cluster_heads.size() 
        << " cluster heads out of " << nodes.size() << " nodes" << std::endl;
    
    // Step 2: Assign nodes to clusters
    std::map<uint64_t, uint64_t> node_to_cluster = assign_to_clusters(nodes, cluster_heads, wireless_range);
    
    // Step 3: Build cluster information
    std::vector<ClusterInfo> clusters;
    
    // Determine number of clusters
    uint32_t max_cluster_id = 0;
    for (const auto& pair : node_to_cluster) {
        max_cluster_id = std::max(max_cluster_id, static_cast<uint32_t>(pair.second));
    }
    
    // If no clusters formed, create one per node (or none)
    if (max_cluster_id == 0) {
        std::cout << "[WARN] " << "No clusters formed; returning empty result" << std::endl;
        return {};
    }
    
    // Resize clusters to max_cluster_id + 1
    clusters.resize(max_cluster_id + 1);
    
    // Populate cluster information
    for (const auto& pair : node_to_cluster) {
        uint64_t node_id = pair.first;
        uint32_t cluster_id = pair.second;
        
        auto& cluster = clusters[cluster_id];
        cluster.cluster_id = cluster_id;
        cluster.member_ids.push_back(node_id);
        cluster.member_count++;
        
        // Find the node and get its residual energy
        auto node_it = std::find_if(nodes.begin(), nodes.end(),
            [&](const std::shared_ptr<Node>& n) { return n->get_id().id == node_id; });
        if (node_it != nodes.end()) {
            cluster.total_residual_energy += (*node_it)->get_residual_battery();
        }
    }
    
    // Set cluster head for each cluster
    for (uint64_t head_id : cluster_heads) {
        auto head_it = std::find_if(nodes.begin(), nodes.end(),
            [&](const std::shared_ptr<Node>& n) { return n->get_id().id == head_id; });
        if (head_it != nodes.end()) {
            // Find which cluster this head belongs to
            for (auto& cluster : clusters) {
                if (std::find(cluster.member_ids.begin(), cluster.member_ids.end(), head_id) != cluster.member_ids.end()) {
                    cluster.cluster_head_id = head_id;
                    break;
                }
            }
        }
    }
    
    // Print summary
    for (const auto& cluster : clusters) {
        std::cout << "Cluster " << cluster.cluster_id 
            << ": head=" << cluster.cluster_head_id 
            << ", members=" << cluster.member_count
            << ", avg_energy=" << (cluster.total_residual_energy / cluster.member_count) << std::endl;
    }
    
    return clusters;
}

std::vector<uint64_t> HEED::select_cluster_heads(
    const std::vector<std::shared_ptr<Node>>& nodes,
    double wireless_range) {
    
    std::cout << "[DEBUG] " << "Selecting cluster heads from " << nodes.size() << " nodes" << std::endl;
    
    std::vector<uint64_t> cluster_heads;
    cluster_heads.reserve(nodes.size());
    
    int N = static_cast<int>(nodes.size());
    double p = params_.initial_cluster_head_probability;
    double alpha = 1.0;  // energy weight exponent
    double beta = 2.0;   // distance weight exponent
    
    // Step 1: Tentative cluster-head selection (probabilistic)
    // Each node becomes a tentative CH with probability p
    // Then, nodes with higher residual energy and closer communication cost are preferred
    
    std::vector<bool> is_tentative_CH(N, false);
    
    // Use deterministic selection based on HEED algorithm
    // With probability p, node can be a CH; then we rank by suitability
    
    // For reproducibility with seed, use node ID-based random
    for (int i = 0; i < N; i++) {
        // HEED: become CH with probability p * (E_i / E_max)^α * (1 / d_i^β)
        // Where d_i is the average distance to other nodes
        
        // Compute residual energy ratio
        double max_energy = 0.0;
        for (const auto& node : nodes) {
            max_energy = std::max(max_energy, node->get_residual_battery());
        }
        double energy_ratio = 1.0;
        if (max_energy > 0) {
            energy_ratio = nodes[i]->get_residual_battery() / max_energy;
        }
        
        // Compute average distance to other nodes
        double avg_dist = 0.0;
        for (int j = 0; j < N; j++) {
            if (i == j) continue;
            double dist = nodes[i]->get_position().distance_to(nodes[j]->get_position());
            avg_dist += dist;
        }
        if (N > 1) avg_dist /= (N - 1);
        
        // Normalize distance: smaller distance = higher probability
        // Max possible distance in 1000x1000 area ~1414m
        double max_possible_dist = 1414.0;  // sqrt(1000^2 + 1000^2)
        double distance_factor = 1.0 - (avg_dist / max_possible_dist);
        
        // HEED probability: p * (E_ratio)^alpha * (distance_factor)^beta
        double heid_prob = p * std::pow(energy_ratio, alpha) * std::pow(distance_factor, beta);
        
        // Use deterministic but varied selection based on node ID
        // hash node_id to get a pseudo-random value
        uint64_t h = nodes[i]->get_id().id;
        h = (h * 0x9e3779b97f4a7c15ULL) & 0xFFFFFFFFFFFFFFFFULL;  // simple multiply-shift
        double rand_val = static_cast<double>(h & 0xFFFFFFFF) / static_cast<double>(0xFFFFFFFFFFFFFFFFULL);
        
        if (rand_val < heid_prob) {
            is_tentative_CH[i] = true;
            cluster_heads.push_back(nodes[i]->get_id().id);
        }
    }
    
    std::cout << "[DEBUG] " << "Tentative cluster heads: " << cluster_heads.size() << std::endl;
    
    // Step 2: Final cluster-head selection
    // If a node is selected as CH, it stays; if not, it becomes a member
    // If multiple nodes are too close, resolve ties by energy
    
    // For now, keep all tentative CHs
    // In full HEED, if a node is within communication range of another CH,
    // the one with lower suitability resigns
    
    // Sort cluster heads by suitability (energy * 1/distance)
    // This helps with later reassignment
    
    return cluster_heads;
}

std::map<uint64_t, uint64_t> HEED::assign_to_clusters(
    const std::vector<std::shared_ptr<Node>>& nodes,
    const std::vector<uint64_t>& cluster_heads,
    double wireless_range) {
    
    std::cout << "[DEBUG] " << "Assigning " << nodes.size() << " nodes to " 
        << cluster_heads.size() << " clusters" << std::endl;
    
    std::map<uint64_t, uint64_t> node_to_cluster;
    
    if (cluster_heads.empty()) {
        std::cout << "[WARN] " << "No cluster heads assigned" << std::endl;
        return node_to_cluster;
    }
    
    int N = static_cast<int>(nodes.size());
    int H = static_cast<int>(cluster_heads.size());
    
    // For each non-CH node, assign to the nearest cluster head within range
    for (int i = 0; i < N; i++) {
        uint64_t node_id = nodes[i]->get_id().id;
        
        // Skip if this node is a cluster head
        bool is_CH = false;
        for (uint64_t head_id : cluster_heads) {
            if (head_id == node_id) {
                is_CH = true;
                break;
            }
        }
        if (is_CH) {
            // Cluster heads belong to their own cluster
            // Find which cluster this head leads
            for (size_t j = 0; j < cluster_heads.size(); j++) {
                if (cluster_heads[j] == node_id) {
                    node_to_cluster[node_id] = static_cast<uint64_t>(j);
                    break;
                }
            }
            continue;
        }
        
        // Find nearest cluster head within wireless range
        double min_dist = wireless_range + 1.0;  // start above range
        uint64_t best_head = 0;
        
        for (uint64_t head_id : cluster_heads) {
            // Find the node object for this head
            auto head_it = std::find_if(nodes.begin(), nodes.end(),
                [&](const std::shared_ptr<Node>& n) { return n->get_id().id == head_id; });
            if (head_it == nodes.end()) continue;
            
            double dist = nodes[i]->get_position().distance_to((*head_it)->get_position());
            if (dist < min_dist && dist <= wireless_range) {
                min_dist = dist;
                best_head = head_id;
            }
        }
        
        if (best_head != 0) {
            node_to_cluster[node_id] = best_head;
        } else {
            // Node cannot reach any cluster head - ad hoc mode
            // Assign to a default "unclustered" group
            node_to_cluster[node_id] = 0;  // cluster 0 = unclustered
        }
    }
    
    return node_to_cluster;
}

bool HEED::rotate_cluster_head(
    std::shared_ptr<Node> old_head,
    std::vector<std::shared_ptr<Node>>& nodes,
    double wireless_range) {
    
    std::cout << "Rotating cluster head for node " << old_head->get_id().id << std::endl;
    
    if (!old_head) return false;
    
    // Find the cluster this head belongs to
    // Re-select a new head from the members of the cluster
    // Ideally from members with good residual energy and reasonable distance
    
    // Find all members of the old head's cluster
    std::vector<std::shared_ptr<Node>> cluster_members;
    for (const auto& node : nodes) {
        // A node is a member if it's within range of the old head
        double dist = old_head->get_position().distance_to(node->get_position());
        if (dist <= wireless_range && node->get_id().id != old_head->get_id().id) {
            cluster_members.push_back(node);
        }
    }
    
    if (cluster_members.empty()) {
        std::cout << "[WARN] " << "No members available for new cluster head selection" << std::endl;
        return false;
    }
    
    // Select new head: node with highest residual energy among members
    // (could also use HEED probability)
    std::shared_ptr<Node> best_member = cluster_members[0];
    double best_energy = best_member->get_residual_battery();
    
    for (const auto& member : cluster_members) {
        double energy = member->get_residual_battery();
        if (energy > best_energy) {
            best_energy = energy;
            best_member = member;
        }
    }
    
    // Update the new head's status
    best_member->set_cluster_head(true);
    old_head->set_cluster_head(false);
    
    std::cout << "New cluster head: " << best_member->get_id().id 
        << " with energy " << best_member->get_residual_battery() << std::endl;
    
    return true;
}

std::map<uint64_t, uint64_t> HEED::reassignment_after_failure(
    std::shared_ptr<Node> failed_head,
    const std::vector<std::shared_ptr<Node>>& nodes,
    double wireless_range) {
    
    std::cout << "Reassigning nodes after cluster head failure: " 
        << failed_head->get_id().id << std::endl;
    
    std::map<uint64_t, uint64_t> new_assignments;
    
    if (!failed_head) return new_assignments;
    
    // Find members of the failed head's cluster
    std::vector<std::shared_ptr<Node>> cluster_members;
    for (const auto& node : nodes) {
        double dist = failed_head->get_position().distance_to(node->get_position());
        if (dist <= wireless_range && node->get_id().id != failed_head->get_id().id) {
            cluster_members.push_back(node);
        }
    }
    
    if (cluster_members.empty()) {
        std::cout << "[WARN] " << "No members in failed cluster" << std::endl;
        return new_assignments;
    }
    
    // Rotate cluster head
    bool rotated = rotate_cluster_head(failed_head, const_cast<std::vector<std::shared_ptr<Node>>&>(nodes), wireless_range);
    if (!rotated) {
        // Try to reassign members to neighboring clusters
        for (const auto& member : cluster_members) {
            // Find the nearest other cluster head
            double min_dist = wireless_range + 1.0;
            uint64_t best_head = 0;
            
            for (const auto& other_node : nodes) {
                if (other_node->is_cluster_head()) {
                    double dist = member->get_position().distance_to(other_node->get_position());
                    if (dist < min_dist && dist <= wireless_range) {
                        min_dist = dist;
                        best_head = other_node->get_id().id;
                    }
                }
            }
            
            if (best_head != 0) {
                new_assignments[member->get_id().id] = best_head;
            }
        }
    }
    
    return new_assignments;
}

uint32_t HEED::get_cluster_id(std::shared_ptr<Node> node) const {
    // Placeholder: return 0
    (void)node;
    return 0;
}

bool HEED::is_cluster_head(std::shared_ptr<Node> node) const {
    if (!node) return false;
    return node->is_cluster_head();
}

}  // namespace haven