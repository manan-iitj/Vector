#ifndef VECTOR_NETWORK_MANAGER_H
#define VECTOR_NETWORK_MANAGER_H

#include <string>
#include <vector>
#include <map>
#include <mutex>
#include <memory>
#include <cstdint>
#include "node.h"

namespace haven {

// Information about a discovered neighbor
struct NeighborInfo {
    WirelessNodeID id;
    NodePosition position;
    int64_t last_seen;
    double signal_strength;
    bool valid;

    NeighborInfo() : last_seen(0), signal_strength(0), valid(false) {}
};

class NetworkManager {
public:
    NetworkManager();
    ~NetworkManager();
    
    // Node management
    std::shared_ptr<Node> add_node(WirelessNodeID id, NodePosition position, double battery);
    void remove_node(WirelessNodeID id);
    std::shared_ptr<Node> get_node(WirelessNodeID id) const;
    std::vector<std::shared_ptr<Node>> get_all_nodes() const;
    
    // Node discovery
    void discover_neighbors(std::shared_ptr<Node> node);
    void update_neighbor_list(std::shared_ptr<Node> node);
    
    // Node joining/leaving
    bool node_join_request(std::shared_ptr<Node> new_node, std::shared_ptr<Node> joining_node);
    bool node_leave(std::shared_ptr<Node> leaving_node);
    void node_fail(std::shared_ptr<Node> failing_node);
    void node_recover(std::shared_ptr<Node> recovering_node);
    
    // Link management
    void establish_link(std::shared_ptr<Node> a, std::shared_ptr<Node> b);
    void disconnect_link(std::shared_ptr<Node> a, std::shared_ptr<Node> b);
    bool link_exists(std::shared_ptr<Node> a, std::shared_ptr<Node> b) const;
    
    // Cluster management
    void assign_cluster(std::shared_ptr<Node> node, uint32_t cluster_id);
    void elect_cluster_head(std::shared_ptr<Node> candidate);
    
    // Authentication
    bool authenticate_node(std::shared_ptr<Node> node);
    void reject_node(std::shared_ptr<Node> node);
    
    // Leader election
    void start_leader_election(std::shared_ptr<Node> initiator);
    std::shared_ptr<Node> get_current_leader() const;
    void update_leader(std::shared_ptr<Node> new_leader);
    
    int64_t calculate_election_score(std::shared_ptr<Node> node);
    
    // Neighbor discovery
    void trigger_neighbor_discovery();
    
private:
    void node_leave_internal(std::shared_ptr<Node> leaving_node);
    
    // Battery management
    void discharge_node(std::shared_ptr<Node> node, double energy);
    void recharge_node(std::shared_ptr<Node> node, double energy);
    
    // Configuration
    void set_node_limit(size_t limit);
    size_t get_node_limit() const;
    
    // Status
    int64_t get_simulation_time() const;
    void set_simulation_time(int64_t time);
    
private:
    std::map<WirelessNodeID, std::shared_ptr<Node>> nodes_;
    std::map<WirelessNodeID, bool> link_status_;
    mutable std::mutex nodes_mutex_;
    size_t node_limit_;
    int64_t simulation_time_;
    
    // Wireless range check
    bool within_wireless_range(std::shared_ptr<Node> a, std::shared_ptr<Node> b) const;
    
    // Neighbor discovery logic
    void perform_neighbor_discovery(std::shared_ptr<Node> node);
};

}  // namespace haven

#endif // VECTOR_NETWORK_MANAGER_H