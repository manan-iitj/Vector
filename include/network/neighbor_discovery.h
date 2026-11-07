#ifndef VECTOR_NEIGHBOR_DISCOVERY_H
#define VECTOR_NEIGHBOR_DISCOVERY_H

#include <string>
#include <vector>
#include <map>
#include <mutex>
#include <memory>
#include "node.h"
#include "topology/topology_manager.h"

namespace haven {

struct NeighborInfo {
    WirelessNodeID id;
    NodePosition position;
    double last_seen;  // simulation time
    double signal_strength;  // RSSI estimate
    bool valid;  // whether link is currently usable
    
    NeighborInfo() : last_seen(0), signal_strength(0), valid(false) {}
};

class NeighborDiscovery {
public:
    NeighborDiscovery();
    ~NeighborDiscovery();
    
    // Discover neighbors within range
    void discover_neighbors(std::shared_ptr<Node> node, const std::vector<std::shared_ptr<Node>>& all_nodes, double wireless_range);
    void update_neighbor_info(std::shared_ptr<Node> node, const std::vector<std::shared_ptr<Node>>& all_nodes, double wireless_range);
    
    // Get visible neighbors
    std::vector<NeighborInfo> get_visible_neighbors(std::shared_ptr<Node> node) const;
    
    // Signal strength model
    double calculate_rssi(const NodePosition& pos1, const NodePosition& pos2, double range) const;
    
    // Mobility-aware discovery
    void apply_mobility_updates(std::shared_ptr<Node> node, int64_t current_time);
    
    // Link quality tracking
    void update_link_quality(std::shared_ptr<Node> a, std::shared_ptr<Node> b, bool connected);
    
private:
    std::mutex discovery_mutex_;
    
    // Packet loss model
    double calculate_packet_loss(double distance, double range) const;
    
    // Propagation delay
    double calculate_propagation_delay(double distance) const;
};

}  // namespace haven

#endif // VECTOR_NEIGHBOR_DISCOVERY_H