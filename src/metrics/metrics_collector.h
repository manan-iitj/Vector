#ifndef VECTOR_METRICS_COLLECTOR_H
#define VECTOR_METRICS_COLLECTOR_H

#include <string>
#include <vector>
#include <map>
#include <cstdint>

namespace haven {

struct TransmissionRecord {
    uint64_t node_id;
    uint64_t destination_id;
    uint64_t packet_id;
    double timestamp;
    bool success;
};

struct ReceptionRecord {
    uint64_t source_id;
    uint64_t destination_id;
    uint64_t packet_id;
    double timestamp;
    int hop_count;
    double rtt;  // round-trip time
};

struct AuthRecord {
    uint64_t node_id;
    uint64_t peer_id;
    int status;  // AuthStatus enum value
    bool accepted;
    int64_t timestamp;
};

struct ElectionRecord {
    uint64_t node_id;
    int64_t epoch_id;
    uint64_t candidate_id;
    bool is_winner;
    int64_t timestamp;
};

struct BatteryRecord {
    uint64_t node_id;
    double initial_battery;
    double residual_battery;
    double energy_consumed;
    int64_t timestamp;
};

struct RoutingRecord {
    uint64_t node_id;
    uint64_t source;
    uint64_t destination;
    std::vector<uint64_t> route;
    double timestamp;
    bool success;
};

struct FailureRecord {
    uint64_t node_id;
    uint64_t failed_neighbor;
    int64_t timestamp;
    std::string failure_type;
};

struct JoinRecord {
    uint64_t new_node_id;
    uint64_t joining_node_id;
    bool authenticated;
    int64_t timestamp;
    bool success;
};

struct LeaveRecord {
    uint64_t node_id;
    int64_t timestamp;
    std::string reason;
};

class MetricsCollector {
public:
    MetricsCollector();
    ~MetricsCollector();
    
    // Recording methods
    void record_packet_transmission(
        uint64_t node_id,
        uint64_t destination_id,
        uint64_t packet_id,
        double timestamp,
        bool success);
    
    void record_packet_reception(
        uint64_t source_id,
        uint64_t destination_id,
        uint64_t packet_id,
        double timestamp,
        int hop_count,
        double rtt);
    
    void record_authentication_event(
        uint64_t node_id,
        uint64_t peer_id,
        int status,
        bool accepted,
        int64_t timestamp);
    
    void record_election_event(
        uint64_t node_id,
        int64_t epoch_id,
        uint64_t candidate_id,
        bool is_winner,
        int64_t timestamp);
    
    void record_battery_event(
        uint64_t node_id,
        double initial_battery,
        double residual_battery,
        double energy_consumed,
        double timestamp);
    
    void record_routing_update(
        uint64_t node_id,
        uint64_t source,
        uint64_t destination,
        const std::vector<uint64_t>& route,
        double timestamp,
        bool success);
    
    void record_failure_event(
        uint64_t node_id,
        uint64_t failed_neighbor,
        double timestamp,
        const std::string& failure_type);
    
    void record_node_join(
        uint64_t new_node_id,
        uint64_t joining_node_id,
        bool authenticated,
        int64_t timestamp,
        bool success);
    
    void record_node_leave(
        uint64_t node_id,
        double timestamp,
        const std::string& reason);
    
    // Metric calculations
    double calculate_pdr() const;
    double calculate_avg_end_to_end_latency() const;
    int calculate_avg_hop_count() const;
    double calculate_throughput() const;
    double calculate_energy_per_node(uint64_t node_id) const;
    
    // Accessors
    std::vector<BatteryRecord> get_battery_log() const;
    std::vector<AuthRecord> get_auth_log() const;
    std::vector<ElectionRecord> get_election_log() const;
    std::vector<TransmissionRecord> get_transmission_log() const;
    std::vector<ReceptionRecord> get_reception_log() const;
    std::vector<RoutingRecord> get_routing_log() const;
    std::vector<FailureRecord> get_failure_log() const;
    std::vector<JoinRecord> get_join_log() const;
    std::vector<LeaveRecord> get_leave_log() const;
    
    // CSV export
    std::string export_csv(const std::string& filename) const;
    
private:
    std::vector<TransmissionRecord> transmission_log_;
    std::vector<ReceptionRecord> reception_log_;
    std::vector<AuthRecord> auth_log_;
    std::vector<ElectionRecord> election_log_;
    std::vector<BatteryRecord> battery_log_;
    std::vector<RoutingRecord> routing_log_;
    std::vector<FailureRecord> failure_log_;
    std::vector<JoinRecord> join_log_;
    std::vector<LeaveRecord> leave_log_;
};

}  // namespace haven

#endif // VECTOR_METRICS_COLLECTOR_H