#include "security/turboblom.h"
#include <iostream>
#include <cmath>
#include <algorithm>
#include <numeric>
#include <random>

namespace haven {

TurboBlom::TurboBlom() : k_(0), t_(0), N_(0), field_size_bits_(0), mod_(0) {}

TurboBlom::~TurboBlom() {}

bool TurboBlom::setup_authority(int k, int t, int field_size_bits) {
    std::cout << "TurboBlom setup: k=" << k << ", t=" << t 
        << ", field_size=" << field_size_bits << " bits" << std::endl;
    
    std::random_device rd;
    rand_engine_.seed(rd());
    
    if (k <= 0 || t <= 0 || field_size_bits <= 0) {
        std::cerr << "[ERROR] Invalid TurboBlom parameters" << std::endl;
        return false;
    }
    
    k_ = k;
    t_ = t;
    field_size_bits_ = field_size_bits;
    N_ = 1 << k;  // 2^k nodes
    
    if (N_ > (1 << field_size_bits)) {
    std::cout << "[WARN] Field size " << field_size_bits 
        << " may be insufficient for " << N_ << " nodes (need at least " 
        << __builtin_ceil(log2(N_)) << " bits)" << std::endl;
    }
    
    // Set modulus: use a prime close to 2^field_size_bits for modular arithmetic
    // For simplicity, use 2^field_size_bits as the modulus (not a prime, but works for key derivation)
    mod_ = 1;
    for (int i = 0; i < field_size_bits; i++) mod_ *= 2;
    
    // Construct generator matrix G (t x N) with random entries in [0, mod_)
    // Each row k represents polynomial coefficients, column j is node j's share
    generator_matrix_.resize(t_);
    for (int i = 0; i < t_; i++) {
        generator_matrix_[i].resize(N_);
        // Generate random row entries
        for (int j = 0; j < N_; j++) {
            generator_matrix_[i][j] = rand_engine_() % mod_;
        }
    }
    
    std::cout << "TurboBlom authority setup complete: " << N_ 
        << " nodes, tolerance t=" << t_ 
        << ", modulus=" << mod_ << std::endl;
    return true;
}

bool TurboBlom::provision_node(uint64_t node_id, int64_t& key_handle) {
    if (node_secrets_.count(node_id) > 0) {
        std::cout << "[WARN] Node " << node_id << " already provisioned" << std::endl;
        return false;
    }
    
    if (node_id >= N_) {
        std::cerr << "[ERROR] Node ID " << node_id << " exceeds maximum " << N_ - 1 << std::endl;
        return false;
    }
    
    // Generate node-specific secrets: column of the generator matrix
    NodeSecrets secrets;
    secrets.node_id = static_cast<int64_t>(node_id);
    secrets.node_handle.handle = static_cast<uint64_t>(node_id);
    secrets.node_handle.valid = true;
    secrets.node_id = static_cast<int64_t>(node_id);
    
    // Each node gets t shares: the entries in column node_id of G
    // share i = G[i][node_id] for i = 1..t
    secrets.shares.resize(t_);
    secrets.values.resize(t_);
    
    for (int i = 0; i < t_; i++) {
        secrets.shares[i] = static_cast<int64_t>(i);  // share index
        secrets.values[i] = generator_matrix_[i][node_id];  // the actual share
    }
    
    // Public material: node gets its column from G (already computed above)
    // Also store the row evaluations for key derivation
    node_secrets_[node_id] = secrets;
    
    key_handle = static_cast<int64_t>(node_id);
    
    std::cout << "Node " << node_id << " provisioned with TurboBlom secrets (share count=" 
        << t_ << ")" << std::endl;
    return true;
}

bool TurboBlom::derive_pairwise_key(uint64_t node_a_id, uint64_t node_b_id,
                                    PairwiseKey& key_out) {
    if (node_a_id == node_b_id) {
        std::cerr << "[ERROR] Cannot derive pairwise key between same node " << node_a_id << std::endl;
        return false;
    }
    
    if (node_secrets_.find(node_a_id) == node_secrets_.end() ||
        node_secrets_.find(node_b_id) == node_secrets_.end()) {
        std::cerr << "[ERROR] One or both nodes not provisioned" << std::endl;
        return false;
    }
    
    const NodeSecrets& secrets_a = node_secrets_.at(node_a_id);
    const NodeSecrets& secrets_b = node_secrets_.at(node_b_id);
    
    // Blom scheme pairwise key derivation:
    // K_AB = sum_{i=1}^{t} share_A[i] * share_B[i] mod mod_
    // Where share_A[i] = G[i][A] and share_B[i] = G[i][B]
    // This is symmetric: K_AB = K_BA
    
    int64_t pairwise_key = 0;
    
    for (int i = 0; i < t_; i++) {
        // Multiply the i-th share of A with the i-th share of B
        int64_t term = (secrets_a.values[i] * secrets_b.values[i]) % mod_;
        pairwise_key = (pairwise_key + term) % mod_;
    }
    
    // Ensure positive result
    if (pairwise_key < 0) pairwise_key += mod_;
    
    // Convert to byte material
    std::vector<uint8_t> key_material;
    key_material.reserve((field_size_bits_ + 7) / 8);
    
    // Encode the pairwise key as bytes
    for (int i = 0; i < (field_size_bits_ + 7) / 8; i++) {
        key_material.push_back(static_cast<uint8_t>((pairwise_key >> (8 * i)) & 0xFF));
    }
    
    // Build output
    key_out.key_material = key_material;
    key_out.key_length = key_material.size();
    key_out.origin_handle.handle = node_a_id;
    key_out.origin_handle.valid = true;
    key_out.destination_handle.handle = node_b_id;
    key_out.destination_handle.valid = true;
    key_out.epoch = 0;
    
    std::cout << "[DEBUG] Derived pairwise key between node " << node_a_id 
        << " and node " << node_b_id 
        << ": K_AB=0x" << std::hex << pairwise_key 
        << " key_length=" << key_out.key_length << std::endl;
    
    return true;
}

bool TurboBlom::verify_pairwise_key(uint64_t node_a_id, uint64_t node_b_id,
                                    const PairwiseKey& key_a, const PairwiseKey& key_b) {
    if (key_a.key_length != key_b.key_length) {
        std::cerr << "[ERROR] " << "Key length mismatch: A=" << key_a.key_length 
            << " B=" << key_b.key_length << std::endl;
        return false;
    }
    
    // Compare key material
    bool match = true;
    for (size_t i = 0; i < key_a.key_material.size(); i++) {
        if (key_a.key_material[i] != key_b.key_material[i]) {
            match = false;
            break;
        }
    }
    
    if (!match) {
    std::cout << "[WARN] Key disagreement between node " << node_a_id 
        << " and node " << node_b_id << std::endl;
    } else {
    std::cout << "Pairwise key verified: K_AB = K_BA for nodes " 
        << node_a_id << " and " << node_b_id << std::endl;
    }
    
    return match;
}

KeyHandle TurboBlom::get_key_handle(uint64_t node_id) const {
    KeyHandle h;
    h.handle = node_id;
    
    auto it = node_secrets_.find(node_id);
    if (it != node_secrets_.end()) {
        h.valid = it->second.node_handle.valid;
    } else {
        h.valid = false;
    }
    
    return h;
}

}  // namespace haven