#ifndef VECTOR_ROUTING_ENGINE_H
#define VECTOR_ROUTING_ENGINE_H

#include <string>
#include <vector>
#include <memory>
#include <unordered_set>
#include "topology_manager.h"

namespace haven {

class RoutingEngine {
public:
    RoutingEngine();
    ~RoutingEngine();
    
    // Shortest path search
    std::vector<WirelessNodeID> find_shortest_path(
        const TopologyManager::TopologyResult& topo,
        WirelessNodeID source, WirelessNodeID target);
    
    // Hop count
    int count_hops(
        const TopologyManager::TopologyResult& topo,
        WirelessNodeID source, WirelessNodeID target);
    
    // Route existence check
    bool route_exists(
        const TopologyManager::TopologyResult& topo,
        WirelessNodeID source, WirelessNodeID target);
    
    // De Bruijn greedy forwarding
    std::vector<WirelessNodeID> greedy_routing(
        const TopologyManager::TopologyResult& topo,
        WirelessNodeID source, WirelessNodeID target);
    
    // Flooding-based route discovery
    std::vector<WirelessNodeID> flood_route_discovery(
        const TopologyManager::TopologyResult& topo,
        WirelessNodeID source, WirelessNodeID target,
        const std::unordered_set<WirelessNodeID>& visited);
    
    // Find alternate route avoiding blocked nodes
    std::vector<WirelessNodeID> find_alternate_route(
        const TopologyManager::TopologyResult& topo,
        WirelessNodeID source, WirelessNodeID target,
        const std::unordered_set<WirelessNodeID>& blocked);
};

}  // namespace haven

#endif // VECTOR_ROUTING_ENGINE_H