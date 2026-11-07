#ifndef VECTOR_NETWORK_RECOVERY_H
#define VECTOR_NETWORK_RECOVERY_H

#include <string>
#include <vector>
#include <memory>
#include "network/node.h"
#include "topology/topology_manager.h"
#include "recovery/search_protocol.h"

namespace haven {

struct LinkFailure {
    uint64_t node_a;
    uint64_t node_b;
    int64_t detection_time;
    bool recovered;
    std::vector<WirelessNodeID> alternate_route;
    
    LinkFailure() : node_a(0), node_b(0), detection_time(0), recovered(false) {}
};

class NetworkRecovery {
public:
    NetworkRecovery();
    ~NetworkRecovery();
    
    // Detect link failure
    bool detect_link_failure(std::shared_ptr<Node> a,
                              std::shared_ptr<Node> b,
                              NetworkManager& net_mgr);
    
    // Recover link using SEARCH
    bool recover_link(std::shared_ptr<Node> a,
                      std::shared_ptr<Node> b,
                      NetworkManager& net_mgr,
                      SearchProtocol& search_mgr);
    
    // Two-sided SEARCH
    SearchResult two_sided_search(std::shared_ptr<Node> a,
                                   std::shared_ptr<Node> b,
                                   NetworkManager& net_mgr,
                                   SearchProtocol& search_mgr);
    
    // Find alternate route using topology
    bool find_alternate_route(std::shared_ptr<Node> source,
                              std::shared_ptr<Node> target,
                              const TopologyManager::TopologyResult& topo,
                              std::vector<WirelessNodeID>& route,
                              const NetworkManager& net_mgr);
    
    // Record a failure
    void record_failure(uint64_t node_a, uint64_t node_b, int64_t time);
    
    // Get recorded failures
    std::vector<LinkFailure> get_recorded_failures() const;
    
private:
    std::vector<LinkFailure> recorded_failures_;
    std::mutex failures_mutex_;
};

}  // namespace haven

#endif // VECTOR_NETWORK_RECOVERY_H