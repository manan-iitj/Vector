#include "security/crypto_manager.h"
#include <iostream>
#include <cstring>
#include <vector>
#include <algorithm>
#include <random>
#include <sstream>
#include <iomanip>

#ifdef VECTOR_USE_MBEDTLS
#include <mbedtls/md.h>
#include <mbedtls/error.h>
#endif

namespace haven {

CryptoManager::CryptoManager()
    : rng_initialized_(false)
{
}

CryptoManager::~CryptoManager() {
    cleanup();
}

bool CryptoManager::initialize() {
#ifndef VECTOR_USE_MBEDTLS
    // Seed the PRNG with a nondeterministic seed when available
    std::random_device rd;
    rng_.seed(rd());
#endif
    rng_initialized_ = true;

    // Setup TurboBlom authority: N = 2^k nodes, tolerance t, field size in bits
    // k = 4 => 16 nodes, t = 2 => tolerate up to 2 compromised nodes
    if (!turboblom_.setup_authority(4, 2, 128)) {
        std::cerr << "[ERROR] Failed to setup TurboBlom authority" << std::endl;
        return false;
    }

#ifdef VECTOR_USE_MBEDTLS
    std::cout << "CryptoManager initialized successfully (mbedTLS-md SHA-256/HMAC)"
        << std::endl;
#else
    std::cout << "CryptoManager initialized successfully (pure-C++ crypto)"
        << std::endl;
#endif
    return true;
}

void CryptoManager::cleanup() {
    rng_initialized_ = false;
}

uint8_t* CryptoManager::generate_secure_random(size_t length) {
    if (!rng_initialized_) {
        std::cout << "[WARN] RNG not initialized" << std::endl;
        return nullptr;
    }

    uint8_t* buffer = new (std::nothrow) uint8_t[length];
    if (!buffer) return nullptr;

    for (size_t i = 0; i < length; i++) {
        buffer[i] = static_cast<uint8_t>(rng_() & 0xFF);
    }
    return buffer;
}

std::vector<uint8_t> CryptoManager::generate_secure_random_vec(size_t length) {
    uint8_t* buf = generate_secure_random(length);
    if (buf) {
        std::vector<uint8_t> result(buf, buf + length);
        delete[] buf;
        return result;
    }
    return {};
}

namespace {

constexpr uint32_t k[64] = {
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2
};

uint32_t rotr(uint32_t x, uint32_t n) { return (x >> n) | (x << (32 - n)); }

std::vector<uint8_t> sha256_raw(const uint8_t* data, size_t length) {
    uint32_t h0=0x6a09e667,h1=0xbb67ae85,h2=0x3c6ef372,h3=0xa54ff53a;
    uint32_t h4=0x510e527f,h5=0x9b05688c,h6=0x1f83d9ab,h7=0x5be0cd19;

    size_t bit_len = length * 8;
    size_t padded_len = length + 1;
    while ((padded_len * 8) % 512 != 448) padded_len++;
    padded_len += 8;

    std::vector<uint8_t> msg(padded_len, 0);
    if (length > 0) memcpy(msg.data(), data, length);
    msg[length] = 0x80;
    for (int i = 0; i < 8; i++)
        msg[padded_len - 8 + i] = static_cast<uint8_t>((bit_len >> (56 - 8*i)) & 0xFF);

    for (size_t off = 0; off < padded_len; off += 64) {
        uint32_t w[64];
        for (int i = 0; i < 16; i++)
            w[i] = (uint32_t)msg[off + i*4] << 24 |
                   (uint32_t)msg[off + i*4 + 1] << 16 |
                   (uint32_t)msg[off + i*4 + 2] << 8 |
                   (uint32_t)msg[off + i*4 + 3];
        for (int i = 16; i < 64; i++) {
            uint32_t s0 = rotr(w[i-15],7)^rotr(w[i-15],18)^(w[i-15]>>3);
            uint32_t s1 = rotr(w[i-2],17)^rotr(w[i-2],19)^(w[i-2]>>10);
            w[i] = w[i-16] + s0 + w[i-7] + s1;
        }
        uint32_t a=h0,b=h1,c=h2,d=h3,e=h4,f=h5,g=h6,h=h7;
        for (int i = 0; i < 64; i++) {
            uint32_t S1 = rotr(e,6)^rotr(e,11)^rotr(e,25);
            uint32_t ch = (e & f) ^ ((~e) & g);
            uint32_t temp1 = h + S1 + ch + k[i] + w[i];
            uint32_t S0 = rotr(a,2)^rotr(a,13)^rotr(a,22);
            uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
            uint32_t temp2 = S0 + maj;
            h=g; g=f; f=e; e=d+temp1; d=c; c=b; b=a; a=temp1+temp2;
        }
        h0+=a; h1+=b; h2+=c; h3+=d; h4+=e; h5+=f; h6+=g; h7+=h;
    }

    std::vector<uint8_t> out(32);
    for (int i = 0; i < 8; i++) {
        uint32_t val = i==0?h0:i==1?h1:i==2?h2:i==3?h3:i==4?h4:i==5?h5:i==6?h6:h7;
        out[i*4]=(val>>24)&0xFF; out[i*4+1]=(val>>16)&0xFF;
        out[i*4+2]=(val>>8)&0xFF; out[i*4+3]=val&0xFF;
    }
    return out;
}

} // namespace

std::vector<uint8_t> CryptoManager::compute_sha256(const uint8_t* data, size_t length) {
#ifdef VECTOR_USE_MBEDTLS
    uint8_t hash[32];
    int ret = mbedtls_md(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256),
                         data, length, hash);
    if (ret == 0) {
        return std::vector<uint8_t>(hash, hash + 32);
    }
    // Fall through to pure-C++ on error
#endif
    return sha256_raw(data, length);
}

std::vector<uint8_t> CryptoManager::compute_sha256(const std::vector<uint8_t>& data) {
    return compute_sha256(data.data(), data.size());
}

std::vector<uint8_t> CryptoManager::compute_hmac_sha256(
    const uint8_t* key, size_t key_len,
    const uint8_t* data, size_t data_len) {

#ifdef VECTOR_USE_MBEDTLS
    mbedtls_md_context_t ctx;
    mbedtls_md_init(&ctx);
    const mbedtls_md_info_t* md_info =
        mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    if (md_info != nullptr &&
        mbedtls_md_setup(&ctx, md_info, 1) == 0) {  // 1 = HMAC mode
        mbedtls_md_starts(&ctx);
        mbedtls_md_update(&ctx, key, key_len);
        mbedtls_md_update(&ctx, data, data_len);
        uint8_t hmac[32];
        if (mbedtls_md_finish(&ctx, hmac) == 0) {
            mbedtls_md_free(&ctx);
            return std::vector<uint8_t>(hmac, hmac + 32);
        }
        mbedtls_md_free(&ctx);
    }
    // Fall through to pure-C++ on error
#endif

    uint8_t k_block[64] = {0};
    size_t klen = key_len > 64 ? 64 : key_len;
    if (key && key_len > 0) memcpy(k_block, key, klen);
    else if (key_len > 64) {
        auto digested = sha256_raw(key, key_len);
        memcpy(k_block, digested.data(), 32);
        klen = 32;
    }

    std::vector<uint8_t> ipad(64), opad(64);
    for (size_t i = 0; i < 64; i++) {
        ipad[i] = k_block[i] ^ 0x36;
        opad[i] = k_block[i] ^ 0x5c;
    }

    std::vector<uint8_t> inner(ipad.begin(), ipad.end());
    if (data && data_len > 0) inner.insert(inner.end(), data, data + data_len);
    auto inner_hash = sha256_raw(inner.data(), inner.size());

    std::vector<uint8_t> outer(opad.begin(), opad.end());
    outer.insert(outer.end(), inner_hash.begin(), inner_hash.end());
    return sha256_raw(outer.data(), outer.size());
}

std::vector<uint8_t> CryptoManager::compute_hmac_sha256(
    const std::vector<uint8_t>& key,
    const std::vector<uint8_t>& data) {
    return compute_hmac_sha256(
        key.empty() ? nullptr : key.data(), key.size(),
        data.empty() ? nullptr : data.data(), data.size());
}

bool CryptoManager::constant_time_compare(
    const uint8_t* a, const uint8_t* b, size_t len) {
    if (!a || !b) return false;
    uint8_t diff = 0;
    for (size_t i = 0; i < len; i++) {
        diff |= a[i] ^ b[i];
    }
    return diff == 0;
}

bool CryptoManager::constant_time_compare(
    const std::vector<uint8_t>& a, const std::vector<uint8_t>& b) {
    if (a.size() != b.size()) return false;
    if (a.empty()) return true;
    return constant_time_compare(a.data(), b.data(), a.size());
}

std::vector<uint8_t> CryptoManager::derive_key(
    const uint8_t* secret, size_t secret_len,
    const uint8_t* salt, size_t salt_len,
    const std::string& info) {
    // HKDF-Extract: PRK = HMAC(salt, secret)
    std::vector<uint8_t> prk = compute_hmac_sha256(
        salt_len > 0 && salt ? salt : reinterpret_cast<const uint8_t*>(""),
        salt_len > 0 ? salt_len : 0,
        secret, secret_len);

    // HKDF-Expand: OKM = HMAC(PRK, info || 0x01)
    std::vector<uint8_t> expand_input;
    expand_input.insert(expand_input.end(), info.begin(), info.end());
    expand_input.push_back(0x01);
    std::vector<uint8_t> okm = compute_hmac_sha256(
        prk.data(), prk.size(),
        expand_input.data(), expand_input.size());
    return okm;
}

std::vector<uint8_t> CryptoManager::derive_key(
    const std::vector<uint8_t>& secret,
    const std::vector<uint8_t>& salt,
    const std::string& info) {
    return derive_key(
        secret.empty() ? nullptr : secret.data(), secret.size(),
        salt.empty() ? nullptr : salt.data(), salt.size(),
        info);
}

void CryptoManager::secure_cleanup_key(std::vector<uint8_t>& key) {
    if (!key.empty()) {
#ifdef VECTOR_USE_MBEDTLS
        mbedtls_platform_zeroize(key.data(), key.size());
#else
        std::fill(key.begin(), key.end(), uint8_t(0));
#endif
        key.clear();
        key.shrink_to_fit();
    }
}

bool CryptoManager::provision_node(uint64_t node_id, int64_t& key_handle) {
    return turboblom_.provision_node(node_id, key_handle);
}

bool CryptoManager::derive_pairwise_key(uint64_t node_a_id, uint64_t node_b_id,
                                        PairwiseKey& key_out) {
    return turboblom_.derive_pairwise_key(node_a_id, node_b_id, key_out);
}

bool CryptoManager::verify_pairwise_key(uint64_t node_a_id, uint64_t node_b_id,
                                        const PairwiseKey& key_a,
                                        const PairwiseKey& key_b) {
    return turboblom_.verify_pairwise_key(node_a_id, node_b_id, key_a, key_b);
}

}  // namespace haven
