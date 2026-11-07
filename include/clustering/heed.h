#ifndef VECTOR_HEED_H
#define VECTOR_HEED_H

#include <string>
#include <vector>
#include <map>
#include <mutex>
#include <memory>
#include <algorithm>
#include <cstdint>
#include "network/node.h"
#include "network/network_manager.h"

namespace haven {

struct HEEDParams {
    double initial_cluster_head_probability;  // p: probability of becoming CH
    double energy_weight;                      // weight for residual energy
    double distance_weight;                    // weight for communication cost
    
    HEEDParams() : initial_cluster_head_probability(0.1),
                   energy_weight(0.5),
                   distance_weight(0.5) {}
};

struct ClusterInfo {
    uint32_t cluster_id;
    uint64_t cluster_head_id;
    std::vector<uint64_t> member_ids;
    double total_residual_energy;
    size_t member_count;
    
    ClusterInfo() : cluster_id(0), cluster_head_id(0), 
                    total_residual_energy(0), member_count(0) {}
};

class HEED {
public:
    HEED();
    ~HEED();
    
    // Configure HEED parameters
    void set_params(const HEEDParams& params);
    HEEDParams get_params() const;
    
    // Run HEED clustering algorithm
    // Returns cluster information for all clusters
    std::vector<ClusterInfo> run_clustering(
        const std::vector<std::shared_ptr<Node>>& nodes,
        const NetworkManager& net_mgr);
    
    // Select cluster heads based on probability and energy
    std::vector<uint64_t> select_cluster_heads(
        const std::vector<std::shared_ptr<Node>>& nodes, 
        double wireless_range);
    
    // Assign nodes to clusters
    std::map<uint64_t, uint64_t> assign_to_clusters(
        const std::vector<std::shared_ptr<Node>>& nodes,
        const std::vector<uint64_t>& cluster_heads,
        double wireless_range);
    
    // Rotate cluster head after failure
    bool rotate_cluster_head(
        std::shared_ptr<Node> old_head,
        std::vector<std::shared_ptr<Node>>& nodes,
        double wireless_range);
    
    // Reassign nodes after cluster head failure
    std::map<uint64_t, uint64_t> reassignment_after_failure(
        std::shared_ptr<Node> failed_head,
        const std::vector<std::shared_ptr<Node>>& nodes,
        double wireless_range);
    
    // Get cluster for a node
    uint32_t get_cluster_id(std::shared_ptr<Node> node) const;
    
    // Check if node is cluster head
    bool is_cluster_head(std::shared_ptr<Node> node) const;
    
private:
    HEEDParams params_;
    
    // Compute HEED probability for a node
    // P(node becomes CH) = p * (E_residual / E_initial)^α * (1 / d(node, CH_nearest)^β)
    double compute_heed_probability(
        std::shared_ptr<Node> node,
        const std::vector<std::shared_ptr<Node>>& all_nodes,
        double wireless_range,
        const std::vector<uint64_t>& potential_heads);
    
    // Compute communication cost: sum of distances to cluster head
    double compute_communication_cost(
        std::shared_ptr<Node> node,
        uint64_t cluster_head_id,
        const std::vector<std::shared_ptr<Node>>& nodes,
        double wireless_range);
};

}  // namespace haven

#endif // VECTOR_HEED_H
