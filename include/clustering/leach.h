#ifndef VECTOR_LEACH_H
#define VECTOR_LEACH_H

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

struct LEACHParams {
    double ch_probability;   // p: probability of becoming cluster head
    int rounds_per_simulation;  // number of LEACH rounds
    bool tdma_scheduling;    // use TDMA scheduling
    
    LEACHParams() : ch_probability(0.1), rounds_per_simulation(20), tdma_scheduling(true) {}
};

struct LEACHClusterInfo {
    uint32_t cluster_id;
    uint64_t cluster_head_id;
    std::vector<uint64_t> member_ids;
    double total_residual_energy;
    size_t member_count;
    
    LEACHClusterInfo() : cluster_id(0), cluster_head_id(0), 
                        total_residual_energy(0), member_count(0) {}
};

class LEACH {
public:
    LEACH();
    ~LEACH();
    
    // Configure LEACH parameters
    void set_params(const LEACHParams& params);
    LEACHParams get_params() const;
    
    // Run LEED clustering for multiple rounds
    std::vector<LEACHClusterInfo> run_clustering(
        const std::vector<std::shared_ptr<Node>>& nodes,
        const NetworkManager& net_mgr);
    
    // Select cluster heads probabilistically (p=0.1 default)
    std::vector<uint64_t> select_cluster_heads(
        const std::vector<std::shared_ptr<Node>>& nodes,
        double wireless_range);
    
    // Assign nodes to nearest cluster head within range
    std::map<uint64_t, uint64_t> assign_to_clusters(
        const std::vector<std::shared_ptr<Node>>& nodes,
        const std::vector<uint64_t>& cluster_heads,
        double wireless_range);
    
    // Simulate energy consumption for LEACH round
    double simulate_round_energy(
        const std::vector<std::shared_ptr<Node>>& nodes,
        const std::vector<uint64_t>& cluster_heads,
        const std::map<uint64_t,uint64_t>& assignments,
        double wireless_range);
    
private:
    LEACHParams params_;
    
    double compute_cht_probability(
        std::shared_ptr<Node> node,
        const std::vector<std::shared_ptr<Node>>& all_nodes,
        double wireless_range,
        const std::vector<uint64_t>& potential_heads);
};

}  // namespace haven

#endif // VECTOR_LEACH_H
