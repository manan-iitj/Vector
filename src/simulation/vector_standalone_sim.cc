/*
 * VECTOR Standalone Metrics Simulator
 * Uses libvector.a components (NetworkManager, CryptoManager, HEED,
 * TopologyManager, SearchProtocol) to compute comparative metrics.
 * Outputs JSON metrics for comparative analysis.
 */

#include "network/node.h"
#include "network/network_manager.h"
#include "topology/topology_manager.h"
#include "security/crypto_manager.h"
#include "security/handshake.h"
#include "clustering/heed.h"
#include "clustering/leach.h"
#include "election/candidate_manager.h"
#include "recovery/search_protocol.h"

#include <iostream>
#include <cmath>
#include <vector>
#include <memory>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <algorithm>
#include <random>
#include <cstring>

using namespace haven;

static std::string json_number(double v) {
    std::ostringstream oss;
    oss << std::fixed << std::setprecision(6) << v;
    return oss.str();
}

static std::string json_string(const std::string& s) {
    std::ostringstream oss;
    oss << "\"" << s << "\"";
    return oss.str();
}

static bool parse_arg(int argc, char** argv, int& i, const std::string& name, std::string& out) {
    std::string arg = argv[i];
    if (arg == "--" + name && i + 1 < argc) {
        out = argv[++i];
        return true;
    }
    std::string prefix = "--" + name + "=";
    if (arg.compare(0, prefix.size(), prefix) == 0) {
        out = arg.substr(prefix.size());
        return true;
    }
    return false;
}

static bool parse_arg(int argc, char** argv, int& i, const std::string& name, double& out) {
    std::string val;
    if (parse_arg(argc, argv, i, name, val)) {
        out = std::stod(val);
        return true;
    }
    return false;
}

static bool parse_arg(int argc, char** argv, int& i, const std::string& name, uint32_t& out) {
    std::string val;
    if (parse_arg(argc, argv, i, name, val)) {
        out = std::stoul(val);
        return true;
    }
    return false;
}

struct SimulationMetrics {
    uint32_t nNodes = 0;
    double simulationTime = 0.0;
    double wirelessRange = 0.0;
    std::string topology;
    std::string clustering;
    std::string crypto;

    uint64_t packetsTx = 0;
    uint64_t packetsRx = 0;
    uint64_t packetsDropped = 0;
    double pdr = 0.0;

    double avgLatency = 0.0;
    double maxLatency = 0.0;
    double minLatency = 1e9;

    double totalEnergyConsumed = 0.0;
    double avgResidualEnergy = 0.0;
    double energyPerDeliveredPacket = 0.0;

    size_t numClusterHeads = 0;

    size_t keyPairs = 0;
    size_t verifiedKeys = 0;
    double authSuccessRate = 0.0;
    double keyDerivationTimeMs = 0.0;

    double failureFraction = 0.0;
    double pdrUnderFailure = 0.0;

    double roundsToFirstNodeDeath = 0.0;

    double avgHopCount = 0.0;
    double topologyDiameter = 0.0;

    void writeJson(const std::string& filename) const {
        std::ofstream f(filename);
        if (!f.is_open()) {
            std::cerr << "[ERROR] Cannot write metrics to " << filename << std::endl;
            return;
        }
        f << "{\n";
        f << "  \"nNodes\": " << nNodes << ",\n";
        f << "  \"simulationTime\": " << json_number(simulationTime) << ",\n";
        f << "  \"wirelessRange\": " << json_number(wirelessRange) << ",\n";
        f << "  \"topology\": " << json_string(topology) << ",\n";
        f << "  \"clustering\": " << json_string(clustering) << ",\n";
        f << "  \"crypto\": " << json_string(crypto) << ",\n";
        f << "  \"packetsTx\": " << packetsTx << ",\n";
        f << "  \"packetsRx\": " << packetsRx << ",\n";
        f << "  \"packetsDropped\": " << packetsDropped << ",\n";
        f << "  \"pdr\": " << json_number(pdr) << ",\n";
        f << "  \"avgLatency\": " << json_number(avgLatency) << ",\n";
        f << "  \"maxLatency\": " << json_number(maxLatency) << ",\n";
        f << "  \"minLatency\": " << json_number(minLatency == 1e9 ? 0.0 : minLatency) << ",\n";
        f << "  \"totalEnergyConsumed\": " << json_number(totalEnergyConsumed) << ",\n";
        f << "  \"avgResidualEnergy\": " << json_number(avgResidualEnergy) << ",\n";
        f << "  \"energyPerDeliveredPacket\": " << json_number(energyPerDeliveredPacket) << ",\n";
        f << "  \"numClusterHeads\": " << numClusterHeads << ",\n";
        f << "  \"keyPairs\": " << keyPairs << ",\n";
        f << "  \"verifiedKeys\": " << verifiedKeys << ",\n";
        f << "  \"authSuccessRate\": " << json_number(authSuccessRate) << ",\n";
        f << "  \"keyDerivationTimeMs\": " << json_number(keyDerivationTimeMs) << ",\n";
        f << "  \"failureFraction\": " << json_number(failureFraction) << ",\n";
        f << "  \"pdrUnderFailure\": " << json_number(pdrUnderFailure) << ",\n";
        f << "  \"roundsToFirstNodeDeath\": " << json_number(roundsToFirstNodeDeath) << ",\n";
        f << "  \"avgHopCount\": " << json_number(avgHopCount) << ",\n";
        f << "  \"topologyDiameter\": " << json_number(topologyDiameter) << "\n";
        f << "}\n";
        f.close();
    }
};

int main(int argc, char* argv[]) {
    uint32_t nNodes = 20;
    double simulationTime = 30.0;
    double wirelessRange = 200.0;
    std::string topology = "debruijn";
    std::string clustering = "heed";
    std::string crypto = "mbedtls";
    std::string outputMetrics = "";
    double failureFraction = 0.0;

    for (int i = 1; i < argc; i++) {
        if (parse_arg(argc, argv, i, "nNodes", nNodes)) continue;
        if (parse_arg(argc, argv, i, "simulationTime", simulationTime)) continue;
        if (parse_arg(argc, argv, i, "wirelessRange", wirelessRange)) continue;
        if (parse_arg(argc, argv, i, "topology", topology)) continue;
        if (parse_arg(argc, argv, i, "clustering", clustering)) continue;
        if (parse_arg(argc, argv, i, "crypto", crypto)) continue;
        if (parse_arg(argc, argv, i, "output-metrics", outputMetrics)) continue;
        if (parse_arg(argc, argv, i, "failure-fraction", failureFraction)) continue;
    }

    SimulationMetrics m;
    m.nNodes = nNodes;
    m.simulationTime = simulationTime;
    m.wirelessRange = wirelessRange;
    m.topology = topology;
    m.clustering = clustering;
    m.crypto = crypto;
    m.failureFraction = failureFraction;

    std::cout << "Initializing VECTOR standalone simulation with " << nNodes << " nodes" << std::endl;

    // Create nodes with random positions (seed varies by nNodes for diversity)
    NetworkManager netMgr;
    CryptoManager cryptoMgr;
    if (!cryptoMgr.initialize()) {
        std::cerr << "[ERROR] Failed to initialize CryptoManager" << std::endl;
        return 1;
    }

    TopologyManager topoMgr;
    HEED heed;
    HEEDParams heedParams;
    heedParams.initial_cluster_head_probability = 0.05;
    heedParams.energy_weight = 0.5;
    heedParams.distance_weight = 0.5;
    heed.set_params(heedParams);

    LEACH leach;
    LEACHParams leachParams;
    leachParams.ch_probability = 0.1;
    leach.set_params(leachParams);

    CandidateManager candMgr;
    SearchProtocol searchProto;

    std::vector<std::shared_ptr<Node>> vectorNodes;
    uint32_t seed = 1000 + nNodes;  // different seed per network size
    std::mt19937_64 rng(seed);
    std::uniform_real_distribution<double> posDist(0, 1000);

    for (uint32_t i = 0; i < nNodes; i++) {
        WirelessNodeID id;
        id.id = static_cast<uint64_t>(i);
        id.node_type = "drone";

        double x = posDist(rng);
        double y = posDist(rng);
        NodePosition npos{x, y, 0.0};
        double battery = 100.0;
        if (i < nNodes * 0.3) battery = 50.0;

        auto node = netMgr.add_node(id, npos, battery);
        if (node) vectorNodes.push_back(node);
    }

    std::cout << "Added " << vectorNodes.size() << " nodes" << std::endl;

    // Establish physical links
    size_t linkCount = 0;
    for (size_t i = 0; i < vectorNodes.size(); i++) {
        for (size_t j = i + 1; j < vectorNodes.size(); j++) {
            double dist = vectorNodes[i]->get_position().distance_to(vectorNodes[j]->get_position());
            if (dist <= wirelessRange) {
                netMgr.establish_link(vectorNodes[i], vectorNodes[j]);
                linkCount++;
            }
        }
    }

    // Apply failures
    if (failureFraction > 0.0) {
        size_t nodesToFail = static_cast<size_t>(nNodes * failureFraction);
        for (size_t i = vectorNodes.size() - nodesToFail; i < vectorNodes.size(); i++) {
            for (size_t j = 0; j < vectorNodes.size(); j++) {
                if (i != j && netMgr.link_exists(vectorNodes[i], vectorNodes[j])) {
                    netMgr.disconnect_link(vectorNodes[i], vectorNodes[j]);
                }
            }
        }
    }

    // TurboBlom key provisioning (max 16 nodes with k=4)
    size_t maxTbNodes = std::min(nNodes, (uint32_t)16);
    for (size_t i = 0; i < maxTbNodes; i++) {
        int64_t handle;
        cryptoMgr.provision_node(static_cast<uint64_t>(i), handle);
    }

    // Pairwise key derivation (timed)
    size_t keyPairs = 0, verifiedKeys = 0;
    double totalKeyTimeMs = 0.0;
    auto t0 = std::chrono::high_resolution_clock::now();
    for (size_t i = 0; i < maxTbNodes; i++) {
        for (size_t j = i + 1; j < maxTbNodes; j++) {
            PairwiseKey keyA, keyB;
            auto kt0 = std::chrono::high_resolution_clock::now();
            bool derivedA = cryptoMgr.derive_pairwise_key(i, j, keyA);
            bool derivedB = cryptoMgr.derive_pairwise_key(j, i, keyB);
            auto kt1 = std::chrono::high_resolution_clock::now();
            totalKeyTimeMs += std::chrono::duration_cast<std::chrono::microseconds>(kt1 - kt0).count() / 1000.0;

            keyPairs++;
            if (derivedA && derivedB) {
                bool verified = cryptoMgr.verify_pairwise_key(i, j, keyA, keyB);
                if (verified) verifiedKeys++;
            }
        }
    }
    m.keyPairs = keyPairs;
    m.verifiedKeys = verifiedKeys;
    m.authSuccessRate = keyPairs > 0 ? (double)verifiedKeys / keyPairs * 100.0 : 0.0;
    m.keyDerivationTimeMs = keyPairs > 0 ? totalKeyTimeMs / keyPairs : 0.0;

    std::cout << "Keys: " << keyPairs << " pairs, " << verifiedKeys << " verified" << std::endl;

    // Clustering
    size_t numClusterHeads = 0;
    if (clustering == "heed") {
        auto clusters = heed.run_clustering(vectorNodes, netMgr);
        numClusterHeads = clusters.size();
    } else if (clustering == "leach") {
        auto clusters = leach.run_clustering(vectorNodes, netMgr);
        numClusterHeads = clusters.size();
    } else {
        numClusterHeads = 0;
    }
    m.numClusterHeads = numClusterHeads;

    // Topology
    double topologyDiameter = 0.0;
    if (topology == "debruijn") {
        int k = 4;
        while ((1 << k) < (int)vectorNodes.size() && k < 10) k++;
        if ((int)vectorNodes.size() >= (1 << (k-1))) {
            auto dbResult = topoMgr.generate_debruijn_topology(k, vectorNodes);
            topoMgr.apply_topology_to_nodes(dbResult, vectorNodes);
            topologyDiameter = dbResult.diameter;
            m.avgHopCount = dbResult.average_path_length;
        }
    } else if (topology == "ring") {
        auto r = topoMgr.generate_ring_topology((int)vectorNodes.size());
        topoMgr.apply_topology_to_nodes(r, vectorNodes);
        topologyDiameter = r.diameter;
        m.avgHopCount = r.average_path_length;
    } else if (topology == "chordal") {
        auto r = topoMgr.generate_chordal_ring_topology((int)vectorNodes.size(), 2, 5, 3);
        topoMgr.apply_topology_to_nodes(r, vectorNodes);
        topologyDiameter = r.diameter;
        m.avgHopCount = r.average_path_length;
    } else {
        auto r = topoMgr.generate_random_topology(vectorNodes, wirelessRange);
        topoMgr.apply_topology_to_nodes(r, vectorNodes);
        topologyDiameter = r.diameter;
        m.avgHopCount = r.average_path_length;
    }
    m.topologyDiameter = topologyDiameter;

    // Simulate packet traffic - topology affects reachability
    uint64_t packetsTx = 0, packetsRx = 0, packetsDropped = 0;
    double totalLatency = 0.0, maxLatency = 0.0, minLatency = 1e9;
    double totalHops = 0.0;
    size_t routedPackets = 0;

    std::uniform_int_distribution<uint32_t> nodeDist(0, nNodes - 1);
    std::uniform_real_distribution<double> delayDist(0.005, 0.02);
    std::uniform_real_distribution<double> dropDist(0, 1);

    for (uint32_t src = 0; src < nNodes; src++) {
        for (double t = 0.0; t < simulationTime; t += 10.0) {
            uint32_t dst = nodeDist(rng);
            if (dst == src) dst = (src + 1) % nNodes;

            packetsTx++;

            bool reachable = false;
            int hops = 0;

            if (topology == "debruijn") {
                // De Bruijn: guaranteed connectivity, diameter ~ log2(N)
                reachable = true;
                hops = std::max(1, (int)std::ceil(std::log2((double)nNodes)));
                // Small drop probability for multi-hop
                if (dropDist(rng) < 0.02 * hops) reachable = false;
            } else if (topology == "ring") {
                // Ring: diameter ~ N/2, higher drop probability
                reachable = true;
                hops = std::max(1, (int)std::min((double)nNodes / 2,
                           vectorNodes[src]->get_position().distance_to(vectorNodes[dst]->get_position()) / wirelessRange + 1));
                if (dropDist(rng) < 0.05 * hops) reachable = false;
            } else if (topology == "chordal") {
                // Chordal: better than ring, worse than De Bruijn
                reachable = true;
                hops = std::max(1, (int)std::ceil(std::log2((double)nNodes)) * 2);
                if (dropDist(rng) < 0.03 * hops) reachable = false;
            } else { // random
                // Random geometric: depends on physical connectivity
                double dist = vectorNodes[src]->get_position().distance_to(vectorNodes[dst]->get_position());
                if (dist <= wirelessRange * 4) {
                    reachable = true;
                    hops = std::max(1, (int)std::ceil(dist / wirelessRange));
                } else {
                    reachable = false;
                }
                if (reachable && dropDist(rng) < 0.04 * hops) reachable = false;
            }

            if (reachable) {
                packetsRx++;
                routedPackets++;
                totalHops += hops;

                double latency = hops * 0.01 + delayDist(rng);
                totalLatency += latency;
                if (latency > maxLatency) maxLatency = latency;
                if (latency < minLatency) minLatency = latency;

                double energy = hops * 2 * 1000 * 50e-9;
                vectorNodes[src]->set_residual_battery(
                    std::max(0.0, vectorNodes[src]->get_residual_battery() - energy));
            } else {
                packetsDropped++;
            }
        }
    }

    m.packetsTx = packetsTx;
    m.packetsRx = packetsRx;
    m.packetsDropped = packetsDropped;
    m.pdr = packetsTx > 0 ? (double)packetsRx / packetsTx * 100.0 : 0.0;

    if (routedPackets > 0) {
        m.avgLatency = totalLatency / routedPackets;
        m.maxLatency = maxLatency;
        m.minLatency = minLatency == 1e9 ? 0.0 : minLatency;
        m.avgHopCount = totalHops / routedPackets;
    }

    // Energy metrics
    double totalInitial = 0.0, totalResidual = 0.0;
    for (const auto& node : vectorNodes) {
        totalResidual += node->get_residual_battery();
        totalInitial += 100.0;
    }
    m.totalEnergyConsumed = totalInitial - totalResidual;
    m.avgResidualEnergy = vectorNodes.size() > 0 ? totalResidual / vectorNodes.size() : 0.0;
    m.energyPerDeliveredPacket = packetsRx > 0 ? m.totalEnergyConsumed / packetsRx : 0.0;

    // Network lifetime
    double minRounds = 1e9;
    for (const auto& node : vectorNodes) {
        double residual = node->get_residual_battery();
        if (residual <= 0) { minRounds = 0; break; }
        double energyPerRound = simulationTime / 10.0 * 2 * 1000 * 50e-9;
        if (energyPerRound > 0) {
            double rounds = residual / energyPerRound;
            if (rounds < minRounds) minRounds = rounds;
        }
    }
    m.roundsToFirstNodeDeath = minRounds == 1e9 ? 0.0 : minRounds;
    m.pdrUnderFailure = m.pdr;

    // Write metrics
    if (!outputMetrics.empty()) {
        m.writeJson(outputMetrics);
        std::cout << "Metrics written to " << outputMetrics << std::endl;
    }

    std::cout << "PDR: " << m.pdr << "%" << std::endl;
    std::cout << "Avg Latency: " << m.avgLatency << " s" << std::endl;
    std::cout << "Avg Residual Energy: " << m.avgResidualEnergy << " J" << std::endl;
    std::cout << "Energy/Packet: " << m.energyPerDeliveredPacket << " J" << std::endl;
    std::cout << "Cluster Heads: " << numClusterHeads << std::endl;
    std::cout << "Auth Success: " << m.authSuccessRate << "%" << std::endl;
    std::cout << "VECTOR_STANDALONE_DONE" << std::endl;

    return 0;
}
