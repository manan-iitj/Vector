#ifndef VECTOR_CRYPTO_MANAGER_H
#define VECTOR_CRYPTO_MANAGER_H

#include <string>
#include <vector>
#include <memory>
#include <cstdint>
#include <random>

#ifdef VECTOR_USE_MBEDTLS
#include <mbedtls/md.h>
#endif

#include "security/turboblom.h"

namespace haven {

class CryptoManager {
public:
    CryptoManager();
    ~CryptoManager();
    
    bool initialize();
    void cleanup();
    
    // Secure random number generation
    uint8_t* generate_secure_random(size_t length);
    std::vector<uint8_t> generate_secure_random_vec(size_t length);
    
    // Hashing (SHA-256)
    std::vector<uint8_t> compute_sha256(const uint8_t* data, size_t length);
    std::vector<uint8_t> compute_sha256(const std::vector<uint8_t>& data);
    
    // HMAC-SHA256
    std::vector<uint8_t> compute_hmac_sha256(
        const uint8_t* key, size_t key_len,
        const uint8_t* data, size_t data_len);
    std::vector<uint8_t> compute_hmac_sha256(
        const std::vector<uint8_t>& key,
        const std::vector<uint8_t>& data);
    
    // Constant-time comparison
    bool constant_time_compare(const uint8_t* a, const uint8_t* b, size_t len);
    bool constant_time_compare(const std::vector<uint8_t>& a, const std::vector<uint8_t>& b);
    
    // Key derivation (HKDF)
    std::vector<uint8_t> derive_key(
        const uint8_t* secret, size_t secret_len,
        const uint8_t* salt, size_t salt_len,
        const std::string& info);
    std::vector<uint8_t> derive_key(
        const std::vector<uint8_t>& secret,
        const std::vector<uint8_t>& salt,
        const std::string& info);
    
    // Secure key cleanup
    void secure_cleanup_key(std::vector<uint8_t>& key);
    
    // TurboBlom key predistribution
    bool provision_node(uint64_t node_id, int64_t& key_handle);
    bool derive_pairwise_key(uint64_t node_a_id, uint64_t node_b_id,
                             PairwiseKey& key_out);
    bool verify_pairwise_key(uint64_t node_a_id, uint64_t node_b_id,
                             const PairwiseKey& key_a, const PairwiseKey& key_b);
    
private:
    bool rng_initialized_;
    std::mt19937_64 rng_;
    TurboBlom turboblom_;
};

}  // namespace haven

#endif // VECTOR_CRYPTO_MANAGER_H
