#include "energy/energy_model.h"
#include <iostream>
#include <cmath>
#include <algorithm>

namespace haven {

EnergyModel::EnergyModel() {}

EnergyModel::~EnergyModel() {}

void EnergyModel::set_params(const EnergyParams& params) {
    params_ = params;
    std::cout << "[DEBUG] " << "Energy parameters updated" << std::endl;
}

EnergyParams EnergyModel::get_params() const {
    return params_;
}

void EnergyModel::initialize_node(uint64_t node_id, double initial_battery) {
    std::lock_guard<std::mutex> lock(energy_mutex_);
    
    if (initial_battery > 0) {
        residual_battery_[node_id] = initial_battery;
    } else {
        residual_battery_[node_id] = params_.initial_battery;
    }
    
    energy_summary_[node_id] = EnergyConsumption();
    
    std::cout << "Node " << node_id << " initialized with battery "
        << residual_battery_[node_id] << " J" << std::endl;
}

void EnergyModel::consume_tx_energy(uint64_t node_id, size_t num_bits, double distance) {
    std::lock_guard<std::mutex> lock(energy_mutex_);
    
    if (residual_battery_.find(node_id) == residual_battery_.end()) {
        std::cout << "[WARN] " << "Node " << node_id << " not found in energy model" << std::endl;
        return;
    }
    
    // Free-space model: E_tx = E_elec * k + epsilon_mp * k * d^2
    // Simplified: use distance-based model
    double tx_energy = calculate_tx_energy(distance, num_bits);
    
    // Ensure we don't drain battery below 0
    double& battery = residual_battery_[node_id];
    battery = std::max(0.0, battery - tx_energy);
    
    // Update summary
    energy_summary_[node_id].tx_energy += tx_energy;
    energy_summary_[node_id].tx_packets += 1;
    
    std::cout << "[DEBUG] " << "Node " << node_id << " consumed " << tx_energy 
        << " J for transmitting " << num_bits << " bits (dist=" << distance << "m), "
        "residual: " << battery << " J" << std::endl;
}

void EnergyModel::consume_rx_energy(uint64_t node_id, size_t num_bits) {
    std::lock_guard<std::mutex> lock(energy_mutex_);
    
    if (residual_battery_.find(node_id) == residual_battery_.end()) {
        std::cout << "[WARN] " << "Node " << node_id << " not found in energy model" << std::endl;
        return;
    }
    
    // Reception energy: E_rx = E_elec * k
    double rx_energy = params_.rx_energy_per_bit * num_bits;
    
    double& battery = residual_battery_[node_id];
    battery = std::max(0.0, battery - rx_energy);
    
    // Update summary
    energy_summary_[node_id].rx_energy += rx_energy;
    energy_summary_[node_id].rx_packets += 1;
    
    std::cout << "[DEBUG] " << "Node " << node_id << " consumed " << rx_energy 
        << " J for receiving " << num_bits << " bits, "
        "residual: " << battery << " J" << std::endl;
}

void EnergyModel::consume_idle_energy(uint64_t node_id, double seconds) {
    std::lock_guard<std::mutex> lock(energy_mutex_);
    
    if (residual_battery_.find(node_id) == residual_battery_.end()) {
        std::cout << "[WARN] " << "Node " << node_id << " not found in energy model" << std::endl;
        return;
    }
    
    double idle_energy = params_.idle_energy_per_sec * seconds;
    
    double& battery = residual_battery_[node_id];
    battery = std::max(0.0, battery - idle_energy);
    
    // Update summary
    energy_summary_[node_id].idle_energy += idle_energy;
    energy_summary_[node_id].idle_time += static_cast<int64_t>(seconds);
    
    std::cout << "[DEBUG] " << "Node " << node_id << " consumed " << idle_energy 
        << " J for " << seconds << "s idle, residual: " << battery << " J" << std::endl;
}

void EnergyModel::consume_processing_energy(uint64_t node_id, int64_t num_ops) {
    std::lock_guard<std::mutex> lock(energy_mutex_);
    
    if (residual_battery_.find(node_id) == residual_battery_.end()) {
        std::cout << "[WARN] " << "Node " << node_id << " not found in energy model" << std::endl;
        return;
    }
    
    double processing_energy = params_.processing_energy_per_op * num_ops;
    
    double& battery = residual_battery_[node_id];
    battery = std::max(0.0, battery - processing_energy);
    
    // Update summary
    energy_summary_[node_id].processing_energy += processing_energy;
    energy_summary_[node_id].processing_ops += num_ops;
    
    std::cout << "[DEBUG] " << "Node " << node_id << " consumed " << processing_energy 
        << " J for " << num_ops << " processing ops, residual: " << battery << " J" << std::endl;
}

double EnergyModel::get_residual_battery(uint64_t node_id) const {
    std::lock_guard<std::mutex> lock(energy_mutex_);
    
    auto it = residual_battery_.find(node_id);
    if (it != residual_battery_.end()) {
        return it->second;
    }
    return 0.0;
}

EnergyConsumption EnergyModel::get_energy_summary(uint64_t node_id) const {
    std::lock_guard<std::mutex> lock(energy_mutex_);
    
    EnergyConsumption summary;
    auto it = energy_summary_.find(node_id);
    if (it != energy_summary_.end()) {
        summary = it->second;
    }
    return summary;
}

bool EnergyModel::has_sufficient_battery(uint64_t node_id, double required_energy) const {
    double battery = get_residual_battery(node_id);
    return battery >= required_energy;
}

void EnergyModel::record_energy_event(uint64_t node_id, const std::string& event_type,
                                        double energy, int64_t timestamp) {
    std::lock_guard<std::mutex> lock(energy_mutex_);
    
    std::cout << "[DEBUG] " << "Energy event recorded: node " << node_id 
        << ", type: " << event_type 
        << ", energy: " << energy 
        << ", timestamp: " << timestamp << std::endl;
}

}  // namespace haven