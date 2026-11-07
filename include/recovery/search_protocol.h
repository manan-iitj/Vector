#ifndef VECTOR_SEARCH_PROTOCOL_H
#define VECTOR_SEARCH_PROTOCOL_H

#include <string>
#include <vector>
#include <map>
#include <mutex>
#include <memory>
#include <atomic>
#include <cstdint>
#include <unordered_set>
#include "network/node.h"
#include "network/network_manager.h"
#include "topology/topology_manager.h"

namespace haven {

struct SearchPacket {
    uint64_t search_id;        // unique search identifier
    uint64_t origin_node;      // node originating the search
    uint64_t target_endpoint;  // target node ID
    uint64_t previous_hop;     // last known hop before failure
    int hop_count;             // number of hops forward
    int ttl;                   // time-to-live
    int sequence_number;       // for duplicate suppression
    std::vector<uint8_t> auth_info;  // authentication information
    int64_t creation_time;     // when the search was created
    
    SearchPacket() : search_id(0), origin_node(0), target_endpoint(0),
                     previous_hop(0), hop_count(0), ttl(10), 
                     sequence_number(0), creation_time(0) {}
};

struct SearchResult {
    bool success;              // whether a route was found
    std::vector<WirelessNodeID> route;  // discovered path
    int hops;                  // number of hops in the route
    int64_t search_id;         // the search that succeeded
    int64_t time_taken;        // time to find the route
    bool partition_detected;   // whether partition was detected
    
    SearchResult() : success(false), hops(0), search_id(0), 
                     time_taken(0), partition_detected(false) {}
};

class SearchProtocol {
public:
    SearchProtocol();
    ~SearchProtocol();
    
    // Initiate search for a broken link
    SearchResult initiate_search(std::shared_ptr<Node> origin,
                                  std::shared_ptr<Node> target,
                                  const NetworkManager& net_mgr);
    
    // Process a search packet at a node
    bool process_search_packet(const SearchPacket& pkt,
                                std::shared_ptr<Node> current_node,
                                std::vector<std::shared_ptr<Node>>& all_nodes,
                                std::vector<SearchPacket>& forwarding_table,
                                SearchResult& result);
    
    // Generate a new search ID
    uint64_t generate_search_id();
    
    // Check for duplicate searches (loop prevention)
    bool is_duplicate_search(const SearchPacket& pkt,
                              const std::unordered_set<uint64_t>& seen_ids);
    
    // Update routing table with discovered route
    bool update_routing_table(std::shared_ptr<Node> origin,
                               const std::vector<WirelessNodeID>& route,
                               const NetworkManager& net_mgr);
    
    // Cancel an ongoing search
    void cancel_search(uint64_t search_id);
    
    // Check if search has timed out
    bool is_timed_out(int64_t creation_time, int64_t max_duration);

    // Set the current topology for routing-based search
    void set_topology(const TopologyManager::TopologyResult& topo);

private:
    // Internal search helper
    SearchResult perform_search(const SearchPacket& init_pkt,
                                const NetworkManager& net_mgr);
    
    // Internal: route discovery using the stored topology
    std::vector<WirelessNodeID> find_route_via_topology(uint64_t origin_id, uint64_t target_id);

    std::mutex search_mutex_;
    std::map<uint64_t, SearchPacket> active_searches_;  // search_id -> packet
    std::unordered_set<uint64_t> seen_search_ids_;     // for dedup
    
    TopologyManager::TopologyResult topo_;
    bool topo_set_ = false;
};

}  // namespace haven

#endif // VECTOR_SEARCH_PROTOCOL_H