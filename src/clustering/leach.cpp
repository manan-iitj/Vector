#include "clustering/leach.h"
#include <iostream>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <random>

namespace haven {

LEACH::LEACH() {}
LEACH::~LEACH() {}

void LEACH::set_params(const LEACHParams& params) {
    params_ = params;
}

LEACHParams LEACH::get_params() const {
    return params_;
}

std::vector<LEACHClusterInfo> LEACH::run_clustering(
    const std::vector<std::shared_ptr<Node>>& nodes,
    const NetworkManager& net_mgr) {
    
    std::cout << "Running LEACH clustering on " << nodes.size() << " nodes" << std::endl;
    
    if (nodes.empty()) {
        std::cout << "[WARN] " << "No nodes for LEACH clustering" << std::endl;
        return {};
    }
    
    double wireless_range = 200.0;  // from config
    
    // Step 1: Select cluster heads probabilistically (p=0.1 per round)
    std::vector<uint64_t> cluster_heads = select_cluster_heads(nodes, wireless_range);
    
    std::cout << "[DEBUG] " << "Selected " << cluster_heads.size() 
        << " cluster heads out of " << nodes.size() << " nodes" << std::endl;
    
    // Step 2: Assign nodes to nearest cluster head within range
    std::map<uint64_t, uint64_t> node_to_cluster = assign_to_clusters(nodes, cluster_heads, wireless_range);
    
    // Step 3: Build cluster information
    std::vector<LEACHClusterInfo> clusters;
    
    // Determine number of clusters
    uint32_t max_cluster_id = 0;
    for (const auto& pair : node_to_cluster) {
        max_cluster_id = std::max(max_cluster_id, static_cast<uint32_t>(pair.second));
    }
    
    // If no clusters formed, return empty
    if (max_cluster_id == 0 && node_to_cluster.empty()) {
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
    
    return clusters;
}

std::vector<uint64_t> LEACH::select_cluster_heads(
    const std::vector<std::shared_ptr<Node>>& nodes,
    double wireless_range) {
    
    std::cout << "[DEBUG] " << "Selecting cluster heads from " << nodes.size() << " nodes" << std::endl;
    
    std::vector<uint64_t> cluster_heads;
    cluster_heads.reserve(nodes.size());
    
    int N = static_cast<int>(nodes.size());
    double p = params_.ch_probability;
    
    // Use deterministic random based on node ID for reproducibility
    for (size_t i = 0; i < nodes.size(); i++) {
        uint64_t h = nodes[i]->get_id().id;
        h = (h * 0x9e3779b97f4a7c15ULL) & 0xFFFFFFFFFFFFFFFFULL;
        double rand_val = static_cast<double>(h & 0xFFFFFFFF) / static_cast<double>(0xFFFFFFFFFFFFFFFFULL);
        
        // LEACH: node becomes CH with probability p
        if (rand_val < p) {
            cluster_heads.push_back(nodes[i]->get_id().id);
        }
    }
    
    // Guarantee at least one CH
    if (cluster_heads.empty() && !nodes.empty()) {
        cluster_heads.push_back(nodes[0]->get_id().id);
    }
    
    std::cout << "[DEBUG] " << "Tentative cluster heads: " << cluster_heads.size() << std::endl;
    return cluster_heads;
}

std::map<uint64_t, uint64_t> LEACH::assign_to_clusters(
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
    
    // For each non-CH node, assign to nearest cluster head within range
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
            for (size_t j = 0; j < cluster_heads.size(); j++) {
                if (cluster_heads[j] == node_id) {
                    node_to_cluster[node_id] = static_cast<uint64_t>(j);
                    break;
                }
            }
            continue;
        }
        
        // Find nearest cluster head within wireless range
        double min_dist = wireless_range + 1.0;
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
            // Node cannot reach any cluster head - assign to cluster 0
            node_to_cluster[node_id] = 0;
        }
    }
    
    return node_to_cluster;
}

}  // namespace haven
