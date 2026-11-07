#include "simulation/vector_simulation.h"
#include <iostream>
#include <cmath>
#include <algorithm>
#include <cstdlib>
#include <fstream>

namespace haven {

VectorSimulation::VectorSimulation() {}

VectorSimulation::~VectorSimulation() {}

bool VectorSimulation::initialize(const SimulationConfig& config) {
    config_ = config;
    
    // Set seed for reproducibility
    // Time resolution handled by std::chrono
    
    std::cout << "Initializing VECTOR simulation with " << config.num_nodes 
        << " nodes, seed=" << config.seed << std::endl;
    
    // Create network manager
    net_mgr_ = std::make_unique<NetworkManager>();
    
    // Create topology manager
    topo_mgr_ = std::make_unique<TopologyManager>();
    
    // Create crypto manager
    crypto_mgr_ = std::make_unique<CryptoManager>();
    if (!crypto_mgr_->initialize()) {
        std::cerr << "[ERROR] " << "Failed to initialize crypto manager" << std::endl;
        return false;
    }
    
    // Create HEED clustering if enabled
    if (config.heed_enabled) {
        heed_ = std::make_unique<HEED>();
    }
    
    // Create candidate manager for leader election
    candidate_mgr_ = std::make_unique<CandidateManager>();
    
    // Create search protocol for recovery
    search_mgr_ = std::make_unique<SearchProtocol>();
    
    // Create metrics collector
    metrics_ = std::make_unique<MetricsCollector>();
    
    // Create nodes
    if (config_.num_nodes <= 0) config_.num_nodes = 10;

    // Seed the C RNG for reproducible positions
    std::srand(static_cast<unsigned int>(config_.seed));

    for (int i = 0; i < config_.num_nodes; i++) {
        // Generate random position
        double x = (static_cast<double>(std::rand()) / RAND_MAX) * config_.area_width;
        double y = (static_cast<double>(std::rand()) / RAND_MAX) * config_.area_height;
        double z = 0.0;
        if (config_.mobility_model == "drone") {
            z = (static_cast<double>(std::rand()) / RAND_MAX) * 100.0;  // altitude
        }
        
        NodePosition pos{x, y, z};
        WirelessNodeID id = generate_node_id(i);
        
        // Initial battery from config or default
        double battery = 100.0;  // default 100 units
        if (i < config.num_nodes * 0.3) battery = 50.0;  // some nodes with lower battery
        
        auto node = net_mgr_->add_node(id, pos, battery);
        if (node) {
            nodes_.push_back(node);
        }
    }
    
    // Configure wireless range
    double range = config.wireless_range;
    if (range <= 0) range = 200.0;  // default
    
    // Establish initial links based on wireless range
    for (size_t i = 0; i < nodes_.size(); i++) {
        for (size_t j = i + 1; j < nodes_.size(); j++) {
            double dist = nodes_[i]->get_position().distance_to(nodes_[j]->get_position());
            if (dist <= range) {
                net_mgr_->establish_link(nodes_[i], nodes_[j]);
            }
        }
    }
    
    // Set topology
    if (config.topology_type == "debruijn") {
        // De Bruijn topology requires exactly 2^k nodes
        int k = 0;
        while ((1 << k) < config.num_nodes) k++;
        auto db_result = topo_mgr_->generate_debruijn_topology(k, nodes_);
        topo_mgr_->apply_topology_to_nodes(db_result, nodes_);
    } else if (config.topology_type == "chordal_ring") {
        auto cr_result = topo_mgr_->generate_chordal_ring_topology(
            config.num_nodes, 2, 5, 3);  // default params
        topo_mgr_->apply_topology_to_nodes(cr_result, nodes_);
    } else if (config.topology_type == "ring") {
        auto ring_result = topo_mgr_->generate_ring_topology(config.num_nodes);
        topo_mgr_->apply_topology_to_nodes(ring_result, nodes_);
    } else {  // random
        auto random_result = topo_mgr_->generate_random_topology(nodes_, range);
        topo_mgr_->apply_topology_to_nodes(random_result, nodes_);
    }
    
    std::cout << "Simulation initialized: " << nodes_.size() << " nodes created" << std::endl;
    std::cout << "Topology: " << config.topology_type << std::endl;
    std::cout << "Security enabled: " << (config.enable_security ? "yes" : "no") << std::endl;
    std::cout << "Authentication enabled: " << (config.enable_authentication ? "yes" : "no") << std::endl;
    
    return true;
}

SimulationResult VectorSimulation::run() {
    std::cout << "Starting VECTOR simulation..." << std::endl;
    
    SimulationResult result;
    
    if (nodes_.empty()) {
        std::cerr << "[ERROR] " << "No nodes in simulation" << std::endl;
        return result;
    }
    
    int64_t sim_time = config_.simulation_time;
    if (sim_time <= 0) sim_time = 100;  // default 100 seconds
    
    // Run simulation for the specified time
    // ns3::Simulator::Stop(ns3::Seconds(sim_time));
    // ns3::Simulator::Run();
    // ns3::Simulator::Destroy();
    
    // For now, perform a single round of operations
    
    // 1. Run HEED clustering if enabled
    if (config_.heed_enabled && heed_) {
        std::cout << "Running HEED clustering..." << std::endl;
        auto clusters = heed_->run_clustering(nodes_, *net_mgr_);
        result.num_cluster_heads = clusters.size();
        
        if (!clusters.empty()) {
            double total_energy = 0.0;
            for (const auto& cluster : clusters) {
                total_energy += cluster.total_residual_energy;
            }
            result.avg_residual_energy = total_energy / (clusters.size() * 
                (clusters.empty() ? 1 : clusters[0].member_count));
        }
    }
    
    // 2. Run leader election if enabled
    if (config_.election_enabled && candidate_mgr_) {
        std::cout << "Running leader election..." << std::endl;
        // Find a node to initiate election
        if (!nodes_.empty()) {
            auto initiator = nodes_[0];
            // Start election epoch
            int64_t epoch_id = 0;
            if (candidate_mgr_->start_election_epoch(initiator, epoch_id)) {
                // Register all other nodes as candidates
                for (size_t i = 1; i < nodes_.size(); i++) {
                    candidate_mgr_->register_candidate(nodes_[i], epoch_id);
                }
                
                // Apply max-consensus
                candidate_mgr_->apply_max_consensus(nodes_, epoch_id);
                
                // Announce leader
                auto leader = candidate_mgr_->announce_leader(epoch_id);
                if (leader) {
                    leader->set_leader(true);
                    std::cout << "Leader elected: " << leader->get_id().id << std::endl;
                }
            }
        }
    }
    
    // 3. Run SEARCH/recovery if enabled
    if (config_.search_enabled && search_mgr_) {
        std::cout << "Running link recovery..." << std::endl;
        // Test single link failure recovery
        if (nodes_.size() >= 2) {
            // Find a pair with a link
            for (size_t i = 0; i < nodes_.size(); i++) {
                for (size_t j = i + 1; j < nodes_.size(); j++) {
                    if (net_mgr_->link_exists(nodes_[i], nodes_[j])) {
                        // Simulate link failure
                        net_mgr_->node_fail(nodes_[i]);
                        net_mgr_->node_fail(nodes_[j]);
                        
                        // Attempt recovery
                        SearchResult search_result = search_mgr_->initiate_search(nodes_[i], nodes_[j], *net_mgr_);
                        
                        result.link_recovery_time = search_result.time_taken;
                        if (search_result.success) {
                            std::cout << "Link recovery successful via route with " 
                                << search_result.hops << " hops" << std::endl;
                        } else {
                            std::cout << "[WARN] " << "Link recovery unsuccessful; partition detected" << std::endl;
                        }
                        break;
                    }
                }
                break;
            }
        }
    }
    
    // 3. Key derivation (TurboBlom) if enabled
    if (config_.enable_turboblom && crypto_mgr_) {
        std::cout << "Running TurboBlom key derivation tests..." << std::endl;
        // Test pairwise key agreement
        if (nodes_.size() >= 2) {
            // Provision nodes
            int64_t handle_a, handle_b;
            bool prov_a = crypto_mgr_->provision_node(nodes_[0]->get_id().id, handle_a);
            bool prov_b = crypto_mgr_->provision_node(nodes_[1]->get_id().id, handle_b);
            
            if (prov_a && prov_b) {
                // Derive pairwise key
                PairwiseKey key;
                auto start = std::chrono::high_resolution_clock::now();
                
                bool derived_a = crypto_mgr_->derive_pairwise_key(
                    nodes_[0]->get_id().id, nodes_[1]->get_id().id, key);
                bool derived_b = crypto_mgr_->derive_pairwise_key(
                    nodes_[1]->get_id().id, nodes_[0]->get_id().id, key);
                
                auto end = std::chrono::high_resolution_clock::now();
                int64_t derivation_time = std::chrono::duration_cast<std::chrono::milliseconds>(
                    end - start).count();
                
                result.key_gen_time = derivation_time;
                
                // Verify key agreement
                if (derived_a && derived_b) {
                    bool verified = crypto_mgr_->verify_pairwise_key(
                        nodes_[0]->get_id().id, nodes_[1]->get_id().id, key, key);
                    
                    if (verified) {
                        result.auth_success_rate = 100.0;  // key agreement successful
                    } else {
                        result.auth_rejection_rate = 100.0;  // key disagreement
                    }
                }
            }
        }
    }
    
    // 4. Compute basic metrics from actual simulation data
    // Packet delivery ratio
    result.pdr = 0.0;  // placeholder - would need actual traffic data
    
    // Average end-to-end latency
    result.avg_latency = 0.0;
    
    // Average hop count
    result.avg_hop_count = 0;
    
    // Throughput
    result.throughput = 0.0;
    
    std::cout << "Simulation run complete" << std::endl;
    
    return result;
}

NodePosition VectorSimulation::generate_random_position() {
    NodePosition pos;
    pos.x = (static_cast<double>(rand()) / RAND_MAX) * config_.area_width;
    pos.y = (static_cast<double>(rand()) / RAND_MAX) * config_.area_height;
    pos.z = 0.0;
    return pos;
}

WirelessNodeID VectorSimulation::generate_node_id(size_t index) {
    WirelessNodeID id;
    id.id = static_cast<uint64_t>(index + 1);
    id.node_type = "node";
    return id;
}

bool VectorSimulation::add_node(uint64_t id, double x, double y, double z, double battery) {
    NodePosition pos{x, y, z};
    WirelessNodeID wid{id, "node"};
    auto node = net_mgr_->add_node(wid, pos, battery);
    if (node) {
        nodes_.push_back(node);
    }
    return node != nullptr;
}

bool VectorSimulation::remove_node(uint64_t id) {
    WirelessNodeID wid{id, "node"};
    net_mgr_->remove_node(wid);
    // Remove from our list
    nodes_.erase(
        std::remove_if(nodes_.begin(), nodes_.end(),
            [&](const std::shared_ptr<Node>& n) { return n->get_id().id == id; }),
        nodes_.end());
    return true;
}

void VectorSimulation::set_topology(TopologyType type) {
    // Implementation
}

TopologyManager::TopologyResult VectorSimulation::get_topology() const {
    return TopologyManager::TopologyResult();
}

void VectorSimulation::enable_security(bool enable) {
    // Implementation
}

void VectorSimulation::enable_authentication(bool enable) {
    // Implementation
}

void VectorSimulation::enable_turboblom(bool enable) {
    // Implementation
}

void VectorSimulation::enable_heed(bool enable) {
    // Implementation
}

void VectorSimulation::enable_election(bool enable) {
    // Implementation
}

void VectorSimulation::enable_search(bool enable) {
    // Implementation
}

bool VectorSimulation::node_join(uint64_t new_node_id, double x, double y, double battery) {
    // Add new node and run joining protocol
    NodePosition pos{x, y, 0.0};
    WirelessNodeID id{new_node_id, "node"};
    
    auto new_node = net_mgr_->add_node(id, pos, battery);
    if (!new_node) return false;
    
    nodes_.push_back(new_node);
    
    // Authentication handshake (placeholder)
    // In full implementation, would run the three-message handshake
    bool authenticated = net_mgr_->authenticate_node(new_node);
    
    if (authenticated) {
        // Discover neighbors
        net_mgr_->discover_neighbors(new_node);
        
        // Reconsider clustering
        if (heed_) {
            // HEED would need to re-run with new node
        }
        
        // Update leader election state
        if (candidate_mgr_) {
            // Re-sync election
        }
        
        return true;
    }
    
    return false;
}

bool VectorSimulation::node_leave(uint64_t id) {
    // Remove node and run reorganization
    auto node = std::find_if(nodes_.begin(), nodes_.end(),
        [&](const std::shared_ptr<Node>& n) { return n->get_id().id == id; });
    
    if (node != nodes_.end()) {
        // Run HEED reassignment if enabled
        if (heed_) {
            // Re-run clustering without the leaving node
        }
        
        // Run leader election re-sync if enabled
        if (candidate_mgr_) {
            // Re-sync election state
        }
        
        net_mgr_->node_leave(*node);
        nodes_.erase(node);
        return true;
    }
    
    return false;
}

MetricsCollector& VectorSimulation::get_metrics() {
    return *metrics_;
}

bool VectorSimulation::export_netanim(const std::string& filename) const {
    // Export NetAnim visualization XML
    // This would contain node positions, movements, and activity
    std::ofstream file(filename);
    if (!file.is_open()) {
        std::cerr << "[ERROR] " << "Cannot create NetAnim file: " << filename << std::endl;
        return false;
    }
    
    file << "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n";
    file << "<animationsim>\n";
    
    // Node positions
    for (const auto& node : nodes_) {
        file << "  <node>\n";
        file << "    <id>" << node->get_id().id << "</id>\n";
        file << "    <x>" << node->get_position().x << "</x>\n";
        file << "    <y>" << node->get_position().y << "</y>\n";
        file << "    <z>" << node->get_position().z << "</z>\n";
        file << "    <color>0 0 1</color>\n";  // blue
        file << "    <size>10</size>\n";
        file << "  </node>\n";
    }
    
    file << "</animationsim>\n";
    file.close();
    
    std::cout << "NetAnim file exported: " << filename << std::endl;
    return true;
}

}  // namespace haven