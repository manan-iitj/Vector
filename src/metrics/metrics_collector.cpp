#include "metrics/metrics_collector.h"
#include <iostream>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <chrono>
#include <vector>
#include <map>
#include <string>

namespace haven {

MetricsCollector::MetricsCollector() {}

MetricsCollector::~MetricsCollector() {}

void MetricsCollector::record_packet_transmission(
    uint64_t node_id,
    uint64_t destination_id,
    uint64_t packet_id,
    double timestamp,
    bool success) {
    TransmissionRecord record;
    record.node_id = node_id;
    record.destination_id = destination_id;
    record.packet_id = packet_id;
    record.timestamp = timestamp;
    record.success = success;
    
    transmission_log_.push_back(record);
}

void MetricsCollector::record_packet_reception(
    uint64_t source_id,
    uint64_t destination_id,
    uint64_t packet_id,
    double timestamp,
    int hop_count,
    double rtt) {
    ReceptionRecord record;
    record.source_id = source_id;
    record.destination_id = destination_id;
    record.packet_id = packet_id;
    record.timestamp = timestamp;
    record.hop_count = hop_count;
    record.rtt = rtt;
    
    reception_log_.push_back(record);
}

void MetricsCollector::record_authentication_event(
    uint64_t node_id,
    uint64_t peer_id,
    int status,
    bool accepted,
    int64_t timestamp) {
    AuthRecord record;
    record.node_id = node_id;
    record.peer_id = peer_id;
    record.status = status;
    record.accepted = accepted;
    record.timestamp = timestamp;
    
    auth_log_.push_back(record);
}

void MetricsCollector::record_election_event(
    uint64_t node_id,
    int64_t epoch_id,
    uint64_t candidate_id,
    bool is_winner,
    int64_t timestamp) {
    ElectionRecord record;
    record.node_id = node_id;
    record.epoch_id = epoch_id;
    record.candidate_id = candidate_id;
    record.is_winner = is_winner;
    record.timestamp = timestamp;
    
    election_log_.push_back(record);
}

void MetricsCollector::record_battery_event(
    uint64_t node_id,
    double initial_battery,
    double residual_battery,
    double energy_consumed,
    double timestamp) {
    BatteryRecord record;
    record.node_id = node_id;
    record.initial_battery = initial_battery;
    record.residual_battery = residual_battery;
    record.energy_consumed = energy_consumed;
    record.timestamp = timestamp;
    
    battery_log_.push_back(record);
}

void MetricsCollector::record_routing_update(
    uint64_t node_id,
    uint64_t source,
    uint64_t destination,
    const std::vector<uint64_t>& route,
    double timestamp,
    bool success) {
    RoutingRecord record;
    record.node_id = node_id;
    record.source = source;
    record.destination = destination;
    record.route = route;
    record.timestamp = timestamp;
    record.success = success;
    
    routing_log_.push_back(record);
}

void MetricsCollector::record_failure_event(
    uint64_t node_id,
    uint64_t failed_neighbor,
    double timestamp,
    const std::string& failure_type) {
    FailureRecord record;
    record.node_id = node_id;
    record.failed_neighbor = failed_neighbor;
    record.timestamp = timestamp;
    record.failure_type = failure_type;
    
    failure_log_.push_back(record);
}

void MetricsCollector::record_node_join(
    uint64_t new_node_id,
    uint64_t joining_node_id,
    bool authenticated,
    int64_t timestamp,
    bool success) {
    JoinRecord record;
    record.new_node_id = new_node_id;
    record.joining_node_id = joining_node_id;
    record.authenticated = authenticated;
    record.timestamp = timestamp;
    record.success = success;
    
    join_log_.push_back(record);
}

void MetricsCollector::record_node_leave(
    uint64_t node_id,
    double timestamp,
    const std::string& reason) {
    LeaveRecord record;
    record.node_id = node_id;
    record.timestamp = timestamp;
    record.reason = reason;
    
    leave_log_.push_back(record);
}

double MetricsCollector::calculate_pdr() const {
    if (transmission_log_.empty()) return 0.0;
    
    size_t successful = 0;
    for (const auto& rec : transmission_log_) {
        if (rec.success) successful++;
    }
    
    return static_cast<double>(successful) / transmission_log_.size();
}

double MetricsCollector::calculate_avg_end_to_end_latency() const {
    if (reception_log_.empty()) return 0.0;
    
    double total_rtt = 0.0;
    for (const auto& rec : reception_log_) {
        total_rtt += rec.rtt;
    }
    
    return total_rtt / reception_log_.size();
}

int MetricsCollector::calculate_avg_hop_count() const {
    if (reception_log_.empty()) return 0;
    
    int total_hops = 0;
    for (const auto& rec : reception_log_) {
        total_hops += rec.hop_count;
    }
    
    return total_hops / reception_log_.size();
}

double MetricsCollector::calculate_throughput() const {
    // Throughput = total successfully received bytes / simulation time
    // This would need simulation time and packet sizes
    return 0.0;
}

double MetricsCollector::calculate_energy_per_node(uint64_t node_id) const {
    // Find all battery records for this node
    double total_consumed = 0.0;
    
    // Would need access to battery log
    return total_consumed;
}

std::vector<BatteryRecord> MetricsCollector::get_battery_log() const {
    return battery_log_;
}

std::vector<AuthRecord> MetricsCollector::get_auth_log() const {
    return auth_log_;
}

std::vector<ElectionRecord> MetricsCollector::get_election_log() const {
    return election_log_;
}

std::vector<TransmissionRecord> MetricsCollector::get_transmission_log() const {
    return transmission_log_;
}

std::vector<ReceptionRecord> MetricsCollector::get_reception_log() const {
    return reception_log_;
}

std::vector<RoutingRecord> MetricsCollector::get_routing_log() const {
    return routing_log_;
}

std::vector<FailureRecord> MetricsCollector::get_failure_log() const {
    return failure_log_;
}

std::vector<JoinRecord> MetricsCollector::get_join_log() const {
    return join_log_;
}

std::vector<LeaveRecord> MetricsCollector::get_leave_log() const {
    return leave_log_;
}

std::string MetricsCollector::export_csv(const std::string& filename) const {
    std::ofstream file(filename);
    if (!file.is_open()) {
        std::cerr << "[ERROR] " << "Cannot open file: " << filename << std::endl;
        return "";
    }
    
    std::string result;
    
    // PDR
    file << "PDR," << calculate_pdr() << "\n";
    
    // Avg end-to-end latency
    file << "AvgLatency," << calculate_avg_end_to_end_latency() << "\n";
    
    // Avg hop count
    file << "AvgHopCount," << calculate_avg_hop_count() << "\n";
    
    // Throughput
    file << "Throughput," << calculate_throughput() << "\n";
    
    // Summarize energy per node (placeholder)
    file << "EnergyPerNode,placeholder\n";
    
    // Number of cluster heads (placeholder)
    file << "ClusterHeads,placeholder\n";
    
    // Leader election convergence time (placeholder)
    file << "ElectionConvergence,placeholder\n";
    
    // Link failure recovery time (placeholder)
    file << "RecoveryTime,placeholder\n";
    
    // Routing overhead (placeholder)
    file << "RoutingOverhead,placeholder\n";
    
    // Authentication success rate
    file << "AuthSuccessRate,placeholder\n";
    
    // Key generation time (placeholder)
    file << "KeyGenTime,placeholder\n";
    
    // Key storage overhead (placeholder)
    file << "KeyStorageOverhead,placeholder\n";
    
    // Memory consumption (placeholder)
    file << "MemoryConsumption,placeholder\n";
    
    file.close();
    
    return "CSV export completed";
}

}  // namespace haven