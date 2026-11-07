#ifndef VECTOR_ENERGY_MODEL_H
#define VECTOR_ENERGY_MODEL_H

#include <string>
#include <map>
#include <mutex>
#include <memory>
#include "network/node.h"

namespace haven {

struct EnergyParams {
    double tx_energy_per_bit;      // Joules per transmitted bit
    double rx_energy_per_bit;      // Joules per received bit
    double idle_energy_per_sec;    // Joules per second in idle mode
    double processing_energy_per_op; // Joules per processing operation
    double initial_battery;        // Initial battery level (Joules)
    double tx_power_level;         // Transmission power (Watts)
    double rx_power_level;         // Reception power (Watts)
    
    EnergyParams() : tx_energy_per_bit(50e-9),
                     rx_energy_per_bit(50e-9),
                     idle_energy_per_sec(0.001),
                     processing_energy_per_op(1e-9),
                     initial_battery(100.0),
                     tx_power_level(1.0),
                     rx_power_level(1.0) {}
};

struct EnergyConsumption {
    double tx_energy;      // Energy consumed for transmission
    double rx_energy;      // Energy consumed for reception
    double idle_energy;    // Energy consumed in idle mode
    double processing_energy; // Energy for processing
    double total_energy;   // Total energy consumed
    int64_t tx_packets;    // Number of packets transmitted
    int64_t rx_packets;    // Number of packets received
    int64_t idle_time;     // Idle time in seconds
    int64_t processing_ops; // Number of processing operations
    
    EnergyConsumption() : tx_energy(0), rx_energy(0), 
                          idle_energy(0), processing_energy(0),
                          total_energy(0), tx_packets(0),
                          rx_packets(0), idle_time(0), processing_ops(0) {}
};

class EnergyModel {
public:
    EnergyModel();
    ~EnergyModel();
    
    // Configure energy parameters
    void set_params(const EnergyParams& params);
    EnergyParams get_params() const;
    
    // Initialize node with battery
    void initialize_node(uint64_t node_id, double initial_battery = -1.0);
    
    // Energy consumption for transmission
    void consume_tx_energy(uint64_t node_id, size_t num_bits, double distance = 0.0);
    
    // Energy consumption for reception
    void consume_rx_energy(uint64_t node_id, size_t num_bits);
    
    // Energy consumption for idle time
    void consume_idle_energy(uint64_t node_id, double seconds);
    
    // Energy consumption for processing
    void consume_processing_energy(uint64_t node_id, int64_t num_ops);
    
    // Get current battery level
    double get_residual_battery(uint64_t node_id) const;
    
    // Get energy consumption summary
    EnergyConsumption get_energy_summary(uint64_t node_id) const;
    
    // Check if node has sufficient battery
    bool has_sufficient_battery(uint64_t node_id, double required_energy) const;
    
    // Record energy event for metrics
    void record_energy_event(uint64_t node_id, const std::string& event_type, 
                              double energy, int64_t timestamp);
    
private:
    EnergyParams params_;
    std::map<uint64_t, double> residual_battery_;  // node_id -> remaining energy
    std::map<uint64_t, EnergyConsumption> energy_summary_;  // per-node summaries
    mutable std::mutex energy_mutex_;
    
    // Calculate transmission energy based on distance (free-space model)
    double calculate_tx_energy(double distance, size_t num_bits) const;
};

}  // namespace haven

#endif // VECTOR_ENERGY_MODEL_H