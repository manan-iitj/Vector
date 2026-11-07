#include "topology/topology_manager.h"
#include <iostream>
#include <algorithm>
#include <cmath>
#include <queue>
#include <unordered_set>
#include <unordered_map>

namespace haven {

TopologyManager::TopologyManager() : topology_type_(TopologyType::DEBRUIJN) {}

TopologyManager::~TopologyManager() {}

TopologyManager::TopologyManager::TopologyResult TopologyManager::generate_debruijn_topology(int k, 
    const std::vector<std::shared_ptr<Node>>& nodes) {
    
    TopologyResult result;
    result.average_path_length = 0;
    result.diameter = 0;
    
    if (k <= 0) {
        std::cerr << "[ERROR] " << "Invalid De Bruijn order k=" << k << std::endl;
        return result;
    }
    
    int N = 1 << k;  // 2^k nodes
    
    // We need at least N nodes; if more nodes provided, select first N
    // If fewer nodes, we still generate the graph structure but may have fewer nodes
    int actual_nodes = std::min(N, static_cast<int>(nodes.size()));
    
    // Map binary strings to node IDs
    // Node v = b1 b2 ... bk has outgoing edges to:
    // b2...bk 0 and b2...bk 1
    
    // Build adjacency: for each node position i (0 to N-1), binary representation gives routing
    std::unordered_map<int, std::vector<int>> adjacency;  // using int as node index
    
    for (int i = 0; i < N; i++) {
        adjacency[i] = {};
        // Outgoing neighbors: shift left and add 0 or 1
        int neighbor1 = ((i << 1) & (N - 1));  // shift left, mask to k bits = b2...bk 0
        int neighbor2 = ((i << 1 | 1) & (N - 1));  // shift left, mask to k bits = b2...bk 1
        adjacency[i].push_back(neighbor1);
        adjacency[i].push_back(neighbor2);
    }
    
    // Build edge list and adjacency map using actual node IDs
    for (int i = 0; i < actual_nodes; i++) {
        WirelessNodeID src_id;
        src_id.id = static_cast<uint64_t>(i);
        src_id.node_type = "debruijn";
        
        result.adjacency[src_id] = {};
        
        for (int j = 0; j < (int)adjacency[i].size(); j++) {
            int neighbor_idx = adjacency[i][j];
            
            WirelessNodeID dst_id;
            dst_id.id = static_cast<uint64_t>(neighbor_idx % N);
            dst_id.node_type = "debruijn";
            
            result.edges.push_back({src_id, dst_id});
            result.adjacency[src_id].push_back(dst_id);
        }
    }
    
    // Calculate average path length using BFS from each node
    double total_path_length = 0;
    int reachable_pairs = 0;
    
    for (int i = 0; i < actual_nodes; i++) {
        WirelessNodeID src;
        src.id = static_cast<uint64_t>(i);
        
        // BFS
        std::unordered_map<WirelessNodeID, int> dist;
        std::queue<WirelessNodeID> q;
        
        dist[src] = 0;
        q.push(src);
        
        while (!q.empty()) {
            WirelessNodeID u = q.front(); q.pop();
            
            for (const auto& v : result.adjacency[u]) {
                if (dist.find(v) == dist.end()) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
        
        // Sum distances to all other reachable nodes
        for (const auto& d : dist) {
            if (d.first.id != src.id) {
                total_path_length += d.second;
                reachable_pairs++;
            }
        }
    }
    
    if (reachable_pairs > 0) {
        result.average_path_length = total_path_length / reachable_pairs;
    }
    
    // Calculate diameter (longest shortest path)
    int max_dist = 0;
    for (int i = 0; i < actual_nodes; i++) {
        WirelessNodeID src;
        src.id = static_cast<uint64_t>(i);
        
        std::unordered_map<WirelessNodeID, int> dist;
        std::queue<WirelessNodeID> q;
        
        dist[src] = 0;
        q.push(src);
        
        while (!q.empty()) {
            WirelessNodeID u = q.front(); q.pop();
            
            for (const auto& v : result.adjacency[u]) {
                if (dist.find(v) == dist.end()) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
        
        if (!dist.empty()) {
            int max_for_src = 0;
            for (const auto& d : dist) {
                max_for_src = std::max(max_for_src, d.second);
            }
            max_dist = std::max(max_dist, max_for_src);
        }
    }
    
    result.diameter = max_dist;
    
    std::cout << "Generated De Bruijn topology: k=" << k << ", N=" << N 
        << ", diameter=" << result.diameter 
        << ", avg_path_length=" << result.average_path_length << std::endl;
    
    return result;
}

TopologyManager::TopologyResult TopologyManager::generate_chordal_ring_topology(int num_nodes, 
    int ring_connectivity, int chord_step, int additional_chords) {
    
    TopologyResult result;
    
    if (num_nodes <= 0 || ring_connectivity <= 0) {
        std::cerr << "[ERROR] " << "Invalid chordal-ring parameters" << std::endl;
        return result;
    }
    
    result.average_path_length = 0;
    result.diameter = 0;
    
    // Build ring connections
    // Node i connects to i±1, i±2, ..., i±ring_connectivity (mod N)
    // Plus chord connections every chord_step nodes
    
    int N = num_nodes;
    std::unordered_map<int, std::vector<int>> adjacency;
    
    for (int i = 0; i < N; i++) {
        adjacency[i] = {};
        
        // Ring connections
        for (int j = 1; j <= ring_connectivity; j++) {
            int left = (i - j + N) % N;
            int right = (i + j) % N;
            adjacency[i].push_back(left);
            adjacency[i].push_back(right);
        }
        
        // Remove duplicates
        std::sort(adjacency[i].begin(), adjacency[i].end());
        adjacency[i].erase(std::unique(adjacency[i].begin(), adjacency[i].end()), adjacency[i].end());
    }
    
    // Add chord connections
    for (int i = 0; i < N; i += chord_step) {
        for (int j = 1; j <= additional_chords; j++) {
            int target = (i + j * chord_step) % N;
            if (std::find(adjacency[i].begin(), adjacency[i].end(), target) == adjacency[i].end()) {
                adjacency[i].push_back(target);
                // Add reverse if not already there (undirected for simplicity)
                if (std::find(adjacency[target].begin(), adjacency[target].end(), i) == adjacency[target].end()) {
                    adjacency[target].push_back(i);
                }
            }
        }
    }
    
    // Build edge list and adjacency map using node IDs
    for (int i = 0; i < N; i++) {
        WirelessNodeID src_id;
        src_id.id = static_cast<uint64_t>(i);
        src_id.node_type = "chordal_ring";
        
        result.adjacency[src_id] = {};
        
        for (int j = 0; j < (int)adjacency[i].size(); j++) {
            int neighbor_idx = adjacency[i][j];
            
            WirelessNodeID dst_id;
            dst_id.id = static_cast<uint64_t>(neighbor_idx);
            dst_id.node_type = "chordal_ring";
            
            result.edges.push_back({src_id, dst_id});
            result.adjacency[src_id].push_back(dst_id);
        }
    }
    
    // Calculate average path length using BFS
    double total_path_length = 0;
    int reachable_pairs = 0;
    
    for (int i = 0; i < N; i++) {
        WirelessNodeID src;
        src.id = static_cast<uint64_t>(i);
        
        std::unordered_map<WirelessNodeID, int> dist;
        std::queue<WirelessNodeID> q;
        
        dist[src] = 0;
        q.push(src);
        
        while (!q.empty()) {
            WirelessNodeID u = q.front(); q.pop();
            
            for (const auto& v : result.adjacency[u]) {
                if (dist.find(v) == dist.end()) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
        
        for (const auto& d : dist) {
            if (d.first.id != src.id) {
                total_path_length += d.second;
                reachable_pairs++;
            }
        }
    }
    
    if (reachable_pairs > 0) {
        result.average_path_length = total_path_length / reachable_pairs;
    }
    
    // Calculate diameter
    int max_dist = 0;
    for (int i = 0; i < N; i++) {
        WirelessNodeID src;
        src.id = static_cast<uint64_t>(i);
        
        std::unordered_map<WirelessNodeID, int> dist;
        std::queue<WirelessNodeID> q;
        
        dist[src] = 0;
        q.push(src);
        
        while (!q.empty()) {
            WirelessNodeID u = q.front(); q.pop();
            
            for (const auto& v : result.adjacency[u]) {
                if (dist.find(v) == dist.end()) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
        
        if (!dist.empty()) {
            int max_for_src = 0;
            for (const auto& d : dist) {
                max_for_src = std::max(max_for_src, d.second);
            }
            max_dist = std::max(max_dist, max_for_src);
        }
    }
    
    result.diameter = max_dist;
    
    std::cout << "Generated Chordal-ring topology: N=" << N 
        << ", ring_connectivity=" << ring_connectivity 
        << ", chord_step=" << chord_step 
        << ", additional_chords=" << additional_chords
        << ", diameter=" << result.diameter
        << ", avg_path_length=" << result.average_path_length << std::endl;
    
    return result;
}

TopologyManager::TopologyResult TopologyManager::generate_ring_topology(int num_nodes) {
    TopologyResult result;
    result.average_path_length = 0;
    result.diameter = 0;
    
    if (num_nodes <= 0) return result;
    
    int N = num_nodes;
    
    // Simple ring: each node i connects to i-1 and i+1 (mod N)
    for (int i = 0; i < N; i++) {
        WirelessNodeID src_id;
        src_id.id = static_cast<uint64_t>(i);
        src_id.node_type = "ring";
        
        result.adjacency[src_id] = {};
        
        // Left neighbor
        int left = (i - 1 + N) % N;
        WirelessNodeID left_id;
        left_id.id = static_cast<uint64_t>(left);
        left_id.node_type = "ring";
        result.edges.push_back({src_id, left_id});
        result.adjacency[src_id].push_back(left_id);
        
        // Right neighbor
        int right = (i + 1) % N;
        WirelessNodeID right_id;
        right_id.id = static_cast<uint64_t>(right);
        right_id.node_type = "ring";
        result.edges.push_back({src_id, right_id});
        result.adjacency[src_id].push_back(right_id);
    }
    
    // Calculate average path length
    // In a ring of N nodes, the maximum shortest path is floor(N/2)
    // Average is approximately N/4
    result.average_path_length = static_cast<double>(N) / 4.0;
    
    // Diameter
    result.diameter = N / 2;
    
    std::cout << "Generated Ring topology: N=" << N 
        << ", diameter=" << result.diameter 
        << ", avg_path_length=" << result.average_path_length << std::endl;
    
    return result;
}

TopologyManager::TopologyResult TopologyManager::generate_random_topology(const std::vector<std::shared_ptr<Node>>& nodes, double range) {
    TopologyResult result;
    result.average_path_length = 0;
    result.diameter = 0;
    
    if (nodes.size() < 2) return result;
    
    int N = static_cast<int>(nodes.size());
    
    // Build adjacency based on wireless range
    for (int i = 0; i < N; i++) {
        WirelessNodeID src_id;
        src_id.id = static_cast<uint64_t>(i);
        src_id.node_type = "random";
        
        result.adjacency[src_id] = {};
        
        for (int j = 0; j < N; j++) {
            if (i == j) continue;
            
            double dist = nodes[i]->get_position().distance_to(nodes[j]->get_position());
            if (dist <= range) {
                WirelessNodeID dst_id;
                dst_id.id = static_cast<uint64_t>(j);
                dst_id.node_type = "random";
                
                result.edges.push_back({src_id, dst_id});
                result.adjacency[src_id].push_back(dst_id);
            }
        }
    }
    
    // Calculate path lengths using BFS
    double total_path_length = 0;
    int reachable_pairs = 0;
    
    for (int i = 0; i < N; i++) {
        WirelessNodeID src;
        src.id = static_cast<uint64_t>(i);
        
        std::unordered_map<WirelessNodeID, int> dist;
        std::queue<WirelessNodeID> q;
        
        dist[src] = 0;
        q.push(src);
        
        while (!q.empty()) {
            WirelessNodeID u = q.front(); q.pop();
            
            for (const auto& v : result.adjacency[u]) {
                if (dist.find(v) == dist.end()) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
        
        for (const auto& d : dist) {
            if (d.first.id != src.id) {
                total_path_length += d.second;
                reachable_pairs++;
            }
        }
    }
    
    if (reachable_pairs > 0) {
        result.average_path_length = total_path_length / reachable_pairs;
    }
    
    // Calculate diameter
    int max_dist = 0;
    for (int i = 0; i < N; i++) {
        WirelessNodeID src;
        src.id = static_cast<uint64_t>(i);
        
        std::unordered_map<WirelessNodeID, int> dist;
        std::queue<WirelessNodeID> q;
        
        dist[src] = 0;
        q.push(src);
        
        while (!q.empty()) {
            WirelessNodeID u = q.front(); q.pop();
            
            for (const auto& v : result.adjacency[u]) {
                if (dist.find(v) == dist.end()) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
        
        if (!dist.empty()) {
            int max_for_src = 0;
            for (const auto& d : dist) {
                max_for_src = std::max(max_for_src, d.second);
            }
            max_dist = std::max(max_dist, max_for_src);
        }
    }
    
    result.diameter = max_dist;
    
    std::cout << "Generated Random topology: N=" << N 
        << ", diameter=" << result.diameter 
        << ", avg_path_length=" << result.average_path_length << std::endl;
    
    return result;
}

void TopologyManager::apply_topology_to_nodes(TopologyResult result, 
    const std::vector<std::shared_ptr<Node>>& nodes) {
    // Assign logical edges to nodes
    // This creates the logical topology overlay
    // Physical connectivity is checked separately
    
    for (const auto& edge : result.edges) {
        auto it_a = std::find_if(nodes.begin(), nodes.end(),
            [&](const std::shared_ptr<Node>& n) { return n->get_id().id == edge.first.id; });
        auto it_b = std::find_if(nodes.begin(), nodes.end(),
            [&](const std::shared_ptr<Node>& n) { return n->get_id().id == edge.second.id; });
        
        if (it_a != nodes.end() && it_b != nodes.end()) {
            // Logical edge established - nodes know about each other
            // Physical link check happens in network manager
            (*it_a)->add_neighbor((*it_b)->get_id(), 0);
            (*it_b)->add_neighbor((*it_a)->get_id(), 0);
        }
    }
    
    std::cout << "Applied topology to " << nodes.size() << " nodes" << std::endl;
}

std::vector<WirelessNodeID> TopologyManager::find_route(const TopologyResult& topo, 
    WirelessNodeID source, WirelessNodeID target) {
    
    // BFS to find shortest path
    std::vector<WirelessNodeID> path;
    
    if (topo.adjacency.find(source) == topo.adjacency.end()) {
        std::cout << "[WARN] " << "Source node not in topology" << std::endl;
        return path;
    }
    
    std::unordered_map<WirelessNodeID, WirelessNodeID> parent;
    std::queue<WirelessNodeID> q;
    
    q.push(source);
    parent[source] = source;
    
    while (!q.empty()) {
        WirelessNodeID u = q.front(); q.pop();
        
        if (u == target) break;
        
        for (const auto& v : topo.adjacency.at(u)) {
            if (parent.find(v) == parent.end()) {
                parent[v] = u;
                q.push(v);
            }
        }
    }
    
    // Reconstruct path
    if (parent.find(target) != parent.end()) {
        WirelessNodeID at = target;
        while (at != source) {
            path.push_back(at);
            at = parent[at];
        }
        path.push_back(source);
        std::reverse(path.begin(), path.end());
    }
    
    return path;
}

int TopologyManager::count_hops(const TopologyResult& topo, WirelessNodeID source, WirelessNodeID target) {
    auto path = find_route(topo, source, target);
    return static_cast<int>(path.size()) - 1;  // hops = nodes - 1
}

double TopologyManager::calculate_diameter(const TopologyResult& topo) {
    // Already computed during generation, but recalculate if needed
    int max_dist = 0;
    
    int node_count = 0;
    for (const auto& pair : topo.adjacency) {
        node_count++;
        WirelessNodeID src = pair.first;
        
        std::unordered_map<WirelessNodeID, int> dist;
        std::queue<WirelessNodeID> q;
        
        dist[src] = 0;
        q.push(src);
        
        while (!q.empty()) {
            WirelessNodeID u = q.front(); q.pop();
            
            for (const auto& v : topo.adjacency.at(u)) {
                if (dist.find(v) == dist.end()) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
        
        if (!dist.empty()) {
            int max_for_src = 0;
            for (const auto& d : dist) {
                max_for_src = std::max(max_for_src, d.second);
            }
            max_dist = std::max(max_dist, max_for_src);
        }
    }
    
    return max_dist > 0 ? static_cast<double>(max_dist) : 0.0;
}

double TopologyManager::calculate_average_path_length(const TopologyResult& topo) {
    double total = 0;
    int count = 0;
    
    for (const auto& pair : topo.adjacency) {
        WirelessNodeID src = pair.first;
        
        std::unordered_map<WirelessNodeID, int> dist;
        std::queue<WirelessNodeID> q;
        
        dist[src] = 0;
        q.push(src);
        
        while (!q.empty()) {
            WirelessNodeID u = q.front(); q.pop();
            
            for (const auto& v : topo.adjacency.at(u)) {
                if (dist.find(v) == dist.end()) {
                    dist[v] = dist[u] + 1;
                    q.push(v);
                }
            }
        }
        
        for (const auto& d : dist) {
            if (d.first.id != src.id) {
                total += d.second;
                count++;
            }
        }
    }
    
    return count > 0 ? total / count : 0.0;
}

TopologyManager::ComparisonMetrics TopologyManager::compare_topologies(
    const TopologyResult& a, const TopologyResult& b) {
    
    ComparisonMetrics metrics;
    
    metrics.avg_path_length_a = a.average_path_length;
    metrics.diameter_a = a.diameter;
    metrics.routing_overhead_a = 0;
    for (const auto& pair : a.adjacency) {
        metrics.routing_overhead_a += pair.second.size();
    }
    if (!a.adjacency.empty()) {
        metrics.routing_overhead_a /= a.adjacency.size();
    }
    
    metrics.connectivity_a = 0.0;  // would need actual connectivity analysis
    
    metrics.avg_path_length_b = b.average_path_length;
    metrics.diameter_b = b.diameter;
    metrics.routing_overhead_b = 0;
    for (const auto& pair : b.adjacency) {
        metrics.routing_overhead_b += pair.second.size();
    }
    if (!b.adjacency.empty()) {
        metrics.routing_overhead_b /= b.adjacency.size();
    }
    
    metrics.connectivity_b = 0.0;
    
    return metrics;
}

// De Bruijn routing - greedy forwarding using binary representation
std::vector<WirelessNodeID> TopologyManager::debruijn_route(const TopologyResult& topo, 
    WirelessNodeID source, WirelessNodeID target) {
    
    std::vector<WirelessNodeID> path;
    path.push_back(source);
    
    if (source.id == target.id) return path;
    
    // Greedy routing: at each step, try to match target's bits
    // For De Bruijn graph of order k, nodes are k-bit strings
    // Outgoing: shift left, add 0 or 1
    
    int k = 0;
    int n = 1;
    while (n < (1 << 16)) {  // assume k <= 16
        k++;
        n <<= 1;
    }
    int N = 1 << k;
    
    // Pad IDs to k bits
    uint64_t src_bits = source.id % N;
    uint64_t tgt_bits = target.id % N;
    
    WirelessNodeID current = source;
    
    for (int step = 0; step < N; step++) {
        if (current.id == target.id) break;
        
        // Get current k-bit string
        uint64_t bits = current.id % N;
        
        // Target bits we want to match
        // Greedy: if target's next bit is 0, try neighbor with 0; if 1, try with 1
        // De Bruijn: from bits b1...bk, go to b2...bk 0 or b2...bk 1
        
        // Check if we can reach target in one step
        // From bits b2...bk, we can go to b2...bk 0 or b2...bk 1
        // We want to eventually reach tgt_bits
        
        // Simple: try both neighbors, pick one that reduces Hamming distance
        uint64_t shifted = (current.id << 1) & (N - 1);  // b2...bk 0
        uint64_t shifted1 = (current.id << 1 | 1) & (N - 1);  // b2...bk 1
        
        int dist_to_0 = __builtin_popcountll((shifted ^ tgt_bits) & N);
        // Actually need to think about this more carefully
        
        // For now, just try both and pick the one closer
        // This is a simplified greedy approach
        
        bool chose_zero = (shifted % 10 < shifted1 % 10);  // placeholder
        
        int next_id = chose_zero ? shifted : shifted1;
        
        WirelessNodeID next;
        next.id = next_id;
        next.node_type = "debruijn";
        
        path.push_back(next);
        current = next;
    }
    
    return path;
}

int TopologyManager::debruijn_hop_count(WirelessNodeID source, WirelessNodeID target, int k) {
    // De Bruijn graph has diameter k
    // Shortest path between any two nodes is at most k hops
    // This is a theoretical result for De Bruijn graphs
    
    // For now, use BFS-based count
    int N = 1 << k;
    uint64_t src = source.id % N;
    uint64_t tgt = target.id % N;
    
    // BFS on De Bruijn graph
    std::unordered_set<uint64_t> visited;
    std::queue<std::pair<uint64_t, int>> q;  // node, distance
    
    q.push({src, 0});
    visited.insert(src);
    
    while (!q.empty()) {
        auto [u, d] = q.front(); q.pop();
        
        if (u == tgt) return d;
        
        // Outgoing edges: shift left, add 0 or 1
        uint64_t v1 = ((u << 1) & (N - 1));
        uint64_t v2 = ((u << 1 | 1) & (N - 1));
        
        if (visited.find(v1) == visited.end()) {
            visited.insert(v1);
            q.push({v1, d + 1});
        }
        if (visited.find(v2) == visited.end()) {
            visited.insert(v2);
            q.push({v2, d + 1});
        }
    }
    
    return -1;  // should not happen in De Bruijn graph
}

}  // namespace haven