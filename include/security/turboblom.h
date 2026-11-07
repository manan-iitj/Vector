#ifndef VECTOR_TURBOBLOM_H
#define VECTOR_TURBOBLOM_H

#include <string>
#include <vector>
#include <map>
#include <mutex>
#include <cstdint>
#include <memory>
#include <random>

namespace haven {

// Finite field element representation
// Using modular arithmetic over GF(2^m) implicitly
// Blom scheme works over a finite field

struct KeyHandle {
    uint64_t handle;
    bool valid;
    
    KeyHandle() : handle(0), valid(false) {}
    KeyHandle(uint64_t h, bool v) : handle(h), valid(v) {}
};

/// Pairwise key derived from TurboBlom
struct PairwiseKey {
    std::vector<uint8_t> key_material;  // actual key bytes
    size_t key_length;                    // in bytes
    KeyHandle origin_handle;
    KeyHandle destination_handle;
    int64_t epoch;
    
    PairwiseKey() : key_length(0), epoch(0) {}
};

/// Node's secret shares from TurboBlom
struct NodeSecrets {
    // Coefficients of the polynomial shares
    // In Blom, each node gets t shares (where t is tolerance)
    std::vector<int64_t> shares;   // evaluation points
    std::vector<int64_t> values;   // f(i) evaluations
    KeyHandle node_handle;
    int64_t node_id;
    
    NodeSecrets() : node_id(0) {}
};

class TurboBlom {
public:
    TurboBlom();
    ~TurboBlom();
    
    // Trusted setup authority
    bool setup_authority(int k, int t, int field_size_bits);
    
    // Node provisioning - called by trusted authority
    bool provision_node(uint64_t node_id, int64_t& key_handle);
    
    // Pairwise key derivation between two nodes
    bool derive_pairwise_key(uint64_t node_a_id, uint64_t node_b_id,
                            PairwiseKey& key_out);
    
    // Key verification
    bool verify_pairwise_key(uint64_t node_a_id, uint64_t node_b_id,
                            const PairwiseKey& key_a, const PairwiseKey& key_b);
    
    // Get node's key handle
    KeyHandle get_key_handle(uint64_t node_id) const;
    
    // Get number of nodes supported
    int supported_nodes() const { return N_; }
    
    // Tolerance (number of compromised nodes tolerated)
    int tolerance() const { return t_; }
    
private:
    // Finite field operations
    int64_t mod_add(int64_t a, int64_t b, int64_t p);
    int64_t mod_sub(int64_t a, int64_t b, int64_t p);
    int64_t mod_mul(int64_t a, int64_t b, int64_t p);
    int64_t mod_pow(int64_t a, int64_t e, int64_t p);
    
    // Generator matrix construction (Blom matrix)
    void construct_generator_matrix();
    
    // Node-specific secret generation
    void generate_node_secrets(uint64_t node_id);
    
    // Pairwise key derivation math
    int64_t derive_pairwise_key_share(uint64_t node_a, uint64_t node_b);
    
    // Parameters
    int k_;       // scheme parameter: N = 2^k
    int t_;       // tolerance: can tolerate t compromised nodes
    int N_;       // total number of nodes = 2^k
    int field_size_bits_;
    int64_t mod_; // modulus for modular arithmetic

    // Pseudo-random generator for matrix construction
    std::mt19937_64 rand_engine_;
    
    // Generator matrix G (t x N)
    // Each row is a polynomial of degree t-1
    std::vector<std::vector<int64_t>> generator_matrix_;
    
    // Node secrets: shares[i] = f(i) for node i
    std::map<uint64_t, NodeSecrets> node_secrets_;
    
    // Public material distributed to all nodes
    // In TurboBlom, each node gets t rows of the generator matrix
    std::map<uint64_t, std::vector<int64_t>> public_material_;
};

}  // namespace haven

#endif // VECTOR_TURBOBLOM_H