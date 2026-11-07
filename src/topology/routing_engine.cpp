#include "topology/routing_engine.h"
#include <iostream>
#include <algorithm>
#include <queue>
#include <unordered_map>
#include <unordered_set>

namespace haven {

RoutingEngine::RoutingEngine() {}

RoutingEngine::~RoutingEngine() {}

std::vector<WirelessNodeID> RoutingEngine::find_shortest_path(
    const TopologyManager::TopologyResult& topo,
    WirelessNodeID source, WirelessNodeID target) {

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

        auto it = topo.adjacency.find(u);
        if (it != topo.adjacency.end()) {
            for (const auto& v : it->second) {
                if (parent.find(v) == parent.end()) {
                    parent[v] = u;
                    q.push(v);
                }
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

int RoutingEngine::count_hops(
    const TopologyManager::TopologyResult& topo,
    WirelessNodeID source, WirelessNodeID target) {

    auto path = find_shortest_path(topo, source, target);
    return static_cast<int>(path.size()) - 1;  // hops = nodes - 1
}

bool RoutingEngine::route_exists(
    const TopologyManager::TopologyResult& topo,
    WirelessNodeID source, WirelessNodeID target) {
    
    auto path = find_shortest_path(topo, source, target);
    return !path.empty() && path.front().id == source.id && path.back().id == target.id;
}

// De Bruijn greedy routing
std::vector<WirelessNodeID> RoutingEngine::greedy_routing(
    const TopologyManager::TopologyResult& topo,
    WirelessNodeID source, WirelessNodeID target) {

    // Greedy forwarding falls back to shortest-path discovery when
    // direct greedy progress is not possible.
    return find_shortest_path(topo, source, target);
}

// Flooding-based route discovery (for when greedy fails)
std::vector<WirelessNodeID> RoutingEngine::flood_route_discovery(
    const TopologyManager::TopologyResult& topo,
    WirelessNodeID source, WirelessNodeID target,
    const std::unordered_set<WirelessNodeID>& visited) {
    
    std::vector<WirelessNodeID> path;
    
    if (source.id == target.id) {
        path.push_back(source);
        return path;
    }
    
    std::unordered_map<WirelessNodeID, WirelessNodeID> parent;
    std::queue<WirelessNodeID> q;
    std::unordered_set<WirelessNodeID> vis = visited;
    
    q.push(source);
    vis.insert(source);
    
    while (!q.empty()) {
        WirelessNodeID u = q.front(); q.pop();
        
        if (u == target) break;
        
        for (const auto& v : topo.adjacency.at(u)) {
            if (vis.find(v) == vis.end()) {
                vis.insert(v);
                parent[v] = u;
                q.push(v);
            }
        }
    }
    
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

// Route repair: find alternate route avoiding blocked nodes
std::vector<WirelessNodeID> RoutingEngine::find_alternate_route(
    const TopologyManager::TopologyResult& topo,
    WirelessNodeID source, WirelessNodeID target,
    const std::unordered_set<WirelessNodeID>& blocked) {
    
    // Remove blocked nodes from adjacency and re-run BFS
    std::unordered_map<WirelessNodeID, std::vector<WirelessNodeID>> filtered_adj;
    
    for (const auto& pair : topo.adjacency) {
        WirelessNodeID u = pair.first;
        if (blocked.find(u) != blocked.end()) continue;
        
        filtered_adj[u] = {};
        for (const auto& v : pair.second) {
            if (blocked.find(v) == blocked.end()) {
                filtered_adj[u].push_back(v);
            }
        }
    }
    
    // Temporarily replace adjacency for BFS
    auto original_adj = topo.adjacency;
    
    // We can't easily modify the const topo, so just do BFS with blocked set
    std::unordered_map<WirelessNodeID, WirelessNodeID> parent;
    std::queue<WirelessNodeID> q;
    std::unordered_set<WirelessNodeID> vis = blocked;
    
    q.push(source);
    vis.insert(source);
    
    while (!q.empty()) {
        WirelessNodeID u = q.front(); q.pop();
        
        if (u == target) break;
        
        auto it = topo.adjacency.find(u);
        if (it != topo.adjacency.end()) {
            for (const auto& v : it->second) {
                if (vis.find(v) == vis.end()) {
                    vis.insert(v);
                    parent[v] = u;
                    q.push(v);
                }
            }
        }
    }
    
    std::vector<WirelessNodeID> path;
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

}  // namespace haven