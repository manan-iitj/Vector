#ifndef VECTOR_TOPOLOGY_MANAGER_H
#define VECTOR_TOPOLOGY_MANAGER_H

#include <string>
#include <vector>
#include <map>
#include <memory>
#include "network/node.h"

namespace haven {

// Topology types
enum class TopologyType {
    DEBRUIJN,
    CHORDAL_RING,
    RING,
    RANDOM_GRAPH
};

class TopologyManager {
public:
    // Topology result
    struct TopologyResult {
        std::vector<std::pair<WirelessNodeID, WirelessNodeID>> edges;
        std::map<WirelessNodeID, std::vector<WirelessNodeID>> adjacency;
        double average_path_length;
        double diameter;
        int hop_count;
    };

    TopologyManager();
    ~TopologyManager();
    
    // Generate topology
    TopologyResult generate_debruijn_topology(int k, const std::vector<std::shared_ptr<Node>>& nodes);
    TopologyResult generate_chordal_ring_topology(int num_nodes, int ring_connectivity, int chord_step, int additional_chords);
    TopologyResult generate_ring_topology(int num_nodes);
    TopologyResult generate_random_topology(const std::vector<std::shared_ptr<Node>>& nodes, double range);
    
    // Apply topology to nodes (assign logical edges)
    void apply_topology_to_nodes(TopologyResult result, const std::vector<std::shared_ptr<Node>>& nodes);
    
    // Routing
    std::vector<WirelessNodeID> find_route(const TopologyResult& topo, WirelessNodeID source, WirelessNodeID target);
    int count_hops(const TopologyResult& topo, WirelessNodeID source, WirelessNodeID target);
    
    // Topology properties
    double calculate_diameter(const TopologyResult& topo);
    double calculate_average_path_length(const TopologyResult& topo);
    
    // Topology type
    void set_topology_type(TopologyType type);
    TopologyType get_topology_type() const;
    
    // Compare topologies
    struct ComparisonMetrics {
        double avg_path_length_a;
        double diameter_a;
        int routing_overhead_a;
        double connectivity_a;
        double avg_path_length_b;
        double diameter_b;
        int routing_overhead_b;
        double connectivity_b;
    };
    ComparisonMetrics compare_topologies(const TopologyResult& a, const TopologyResult& b);
    
private:
    TopologyType topology_type_;
    
    // De Bruijn graph operations
    TopologyResult build_debruijn(int k);
    std::vector<WirelessNodeID> debruijn_route(const TopologyResult& topo, WirelessNodeID source, WirelessNodeID target);
    int debruijn_hop_count(WirelessNodeID source, WirelessNodeID target, int k);
    
    // Chordal ring operations
    TopologyResult build_chordal_ring(int num_nodes, int ring_connectivity, int chord_step, int additional_chords);
    
    // Physical connectivity check
    bool is_physical_link_valid(std::shared_ptr<Node> a, std::shared_ptr<Node> b, double wireless_range) const;
};

}  // namespace haven

#endif // VECTOR_TOPOLOGY_MANAGER_H