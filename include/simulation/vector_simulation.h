#ifndef VECTOR_SIMULATION_H
#define VECTOR_SIMULATION_H

#include <string>
#include <vector>
#include <memory>
#include "network/network_manager.h"
#include "topology/topology_manager.h"
#include "security/crypto_manager.h"
#include "clustering/heed.h"
#include "election/candidate_manager.h"
#include "recovery/search_protocol.h"
#include "metrics/metrics_collector.h"

namespace haven {

struct SimulationConfig {
    int num_nodes;
    double area_width;
    double area_height;
    double wireless_range;
    double packet_size;
    double data_rate;
    std::string mobility_model;
    double max_speed;
    int simulation_time;
    int seed;
    bool enable_security;
    bool enable_authentication;
    bool enable_turboblom;
    bool heed_enabled;
    bool election_enabled;
    bool search_enabled;
    std::string topology_type;
};

struct SimulationResult {
    double pdr;
    double avg_latency;
    double avg_hop_count;
    double throughput;
    double avg_residual_energy;
    size_t num_cluster_heads;
    double election_convergence_time;
    double link_recovery_time;
    int routing_overhead;
    double auth_success_rate;
    double auth_rejection_rate;
    int64_t key_gen_time;
    size_t key_storage_overhead;
    size_t memory_consumption;
};

class VectorSimulation {
public:
    VectorSimulation();
    ~VectorSimulation();
    
    // Initialize simulation
    bool initialize(const SimulationConfig& config);
    
    // Run simulation
    SimulationResult run();
    
    // Stop simulation
    void stop();
    
    // Node management
    bool add_node(uint64_t id, double x, double y, double z, double battery);
    bool remove_node(uint64_t id);
    
    // Topology
    void set_topology(TopologyType type);
    TopologyManager::TopologyResult get_topology() const;
    
    // Security
    void enable_security(bool enable);
    void enable_authentication(bool enable);
    void enable_turboblom(bool enable);
    
    // Clustering
    void enable_heed(bool enable);
    
    // Election
    void enable_election(bool enable);
    
    // SEARCH/recovery
    void enable_search(bool enable);
    
    // Node joining
    bool node_join(uint64_t new_node_id, double x, double y, double battery);
    bool node_leave(uint64_t id);
    
    // Metrics
    MetricsCollector& get_metrics();
    
    // Visualization
    bool export_netanim(const std::string& filename) const;
    
private:
    SimulationConfig config_;
    std::unique_ptr<NetworkManager> net_mgr_;
    std::unique_ptr<TopologyManager> topo_mgr_;
    std::unique_ptr<CryptoManager> crypto_mgr_;
    std::unique_ptr<HEED> heed_;
    std::unique_ptr<CandidateManager> candidate_mgr_;
    std::unique_ptr<SearchProtocol> search_mgr_;
    std::unique_ptr<MetricsCollector> metrics_;
    
    std::vector<std::shared_ptr<Node>> nodes_;
    
    // Helper methods
    NodePosition generate_random_position();
    WirelessNodeID generate_node_id(size_t index);
};

}  // namespace haven

#endif // VECTOR_SIMULATION_H