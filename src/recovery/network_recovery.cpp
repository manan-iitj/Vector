#include "recovery/network_recovery.h"
#include <iostream>
#include <algorithm>
#include <unordered_set>
#include "topology/routing_engine.h"

namespace haven {

NetworkRecovery::NetworkRecovery() {}

NetworkRecovery::~NetworkRecovery() {}

bool NetworkRecovery::detect_link_failure(std::shared_ptr<Node> a, 
                                           std::shared_ptr<Node> b,
                                           NetworkManager& net_mgr) {
    if (!a || !b) return false;
    
    // Check if link was previously established
    if (!net_mgr.link_exists(a, b)) {
        std::cout << "Link between " << a->get_id().id 
            << " and " << b->get_id().id 
            << " was already disconnected" << std::endl;
        return false;
    }
    
    // Disconnect the link
    net_mgr.disconnect_link(a, b);
    
    std::cout << "Detected and recorded link failure between " 
        << a->get_id().id << " and " << b->get_id().id << std::endl;
    
    // Attempt recovery via SEARCH protocol
    // ... would invoke SearchProtocol here
    
    return true;
}

bool NetworkRecovery::recover_link(std::shared_ptr<Node> a,
                                    std::shared_ptr<Node> b,
                                    NetworkManager& net_mgr,
                                    SearchProtocol& search_mgr) {
    if (!a || !b) return false;
    
    std::cout << "Attempting link recovery between " 
        << a->get_id().id << " and " << b->get_id().id << std::endl;
    
    // Use SEARCH protocol to find alternate route
    SearchResult search_result = search_mgr.initiate_search(a, b, net_mgr);
    
    if (search_result.success) {
        // Route discovered - routing update handled by the simulation layer
        std::cout << "Link recovered via alternate route" << std::endl;
        return true;
    } else {
        std::cout << "[WARN] " << "Link recovery failed; partition detected" << std::endl;
        return false;
    }
}

SearchResult NetworkRecovery::two_sided_search(std::shared_ptr<Node> a,
                                                std::shared_ptr<Node> b,
                                                NetworkManager& net_mgr,
                                                SearchProtocol& search_mgr) {
    // Both endpoints A and B initiate SEARCH packets
    // and try to meet in the middle or find an alternate route
    
    std::cout << "Two-sided SEARCH between " << a->get_id().id 
        << " and " << b->get_id().id << std::endl;
    
    // Initiate search from both ends
    SearchResult result_a = search_mgr.initiate_search(a, b, net_mgr);
    SearchResult result_b = search_mgr.initiate_search(b, a, net_mgr);
    
    // Check if either succeeded
    SearchResult combined;
    combined.success = result_a.success || result_b.success;
    combined.partition_detected = !combined.success;
    
    if (result_a.success) {
        combined.route = result_a.route;
        combined.hops = result_a.hops;
    } else if (result_b.success) {
        combined.route = result_b.route;
        combined.hops = result_b.hops;
    }
    
    return combined;
}

bool NetworkRecovery::find_alternate_route(std::shared_ptr<Node> source,
                                            std::shared_ptr<Node> target,
                                            const TopologyManager::TopologyResult& topo,
                                            std::vector<WirelessNodeID>& route,
                                            const NetworkManager& net_mgr) {
    if (!source || !target) return false;
    
    // Use routing engine to find route
    RoutingEngine router;
    route = router.find_shortest_path(topo, source->get_id(), target->get_id());
    
    if (!route.empty()) {
        std::cout << "Found alternate route with " << route.size() - 1 << " hops" << std::endl;
        return true;
    }
    
    return false;
}

}  // namespace haven