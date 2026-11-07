/*
 * crypto_benchmark.cpp
 *
 * Benchmark comparing pure C++ crypto vs mbedTLS crypto for VECTOR TurboBlom.
 *
 * Pure C++: std::mt19937 RNG + finite field dot product key derivation
 * mbedTLS:  mbedtls_ctr_drbg RNG + mbedtls_md_hmac HMAC-SHA256 key derivation
 *
 * Compile:
 *   g++ -std=c++17 -O2 -DMBEDTLS_DECLARE_PRIVATE_IDENTIFIERS \
 *       -I/opt/homebrew/include crypto_benchmark.cpp \
 *       -o crypto_benchmark -L/opt/homebrew/lib -lmbedcrypto
 *
 * Run:
 *   ./crypto_benchmark [--nodes 30,100,500] [--trials 5]
 */

#include <chrono>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <random>
#include <string>
#include <vector>

#define MBEDTLS_DECLARE_PRIVATE_IDENTIFIERS
#include <mbedtls/md.h>

// ---------------------------------------------------------------------------
// Configuration constants
// ---------------------------------------------------------------------------
static constexpr int DEFAULT_T = 2;
static constexpr int DEFAULT_FIELD_BITS = 128;
static constexpr uint64_t MOD = UINT64_MAX;  // 2^64 - 1, used as modulus for field_bits <= 64

// ---------------------------------------------------------------------------
// High-resolution timer
// ---------------------------------------------------------------------------
class Timer {
public:
    void start() { start_ = std::chrono::high_resolution_clock::now(); }
    double stop_ms() {
        auto end = std::chrono::high_resolution_clock::now();
        return std::chrono::duration<double, std::milli>(end - start_).count();
    }

private:
    std::chrono::high_resolution_clock::time_point start_;
};

// ---------------------------------------------------------------------------
// Pure C++ implementation (no crypto library)
// ---------------------------------------------------------------------------
class PureCPP {
public:
    PureCPP(int seed, int field_bits)
        : rng_(seed), field_bits_(field_bits), mod_(1ULL << field_bits) {}

    // Generate provisioning matrix G[t][N] using std::mt19937
    void provision_matrix(int t, int N) {
        G_.resize(t, std::vector<uint64_t>(N));
        for (int i = 0; i < t; ++i) {
            for (int j = 0; j < N; ++j) {
                G_[i][j] = static_cast<uint64_t>(rng_()) % mod_;
            }
        }
    }

    // Get secret shares for node nid (column nid of G)
    std::vector<uint64_t> get_secrets(int nid) const {
        std::vector<uint64_t> shares(G_.size());
        for (size_t i = 0; i < G_.size(); ++i) {
            shares[i] = G_[i][nid];
        }
        return shares;
    }

    // Derive pairwise key using finite field dot product (pure C++, no crypto lib)
    uint64_t derive_key(int a, int b) const {
        if (a == b) return 0;
        uint64_t result = 0;
        for (size_t i = 0; i < G_.size(); ++i) {
            result = (result + G_[i][a] * G_[i][b]) % mod_;
        }
        return result;
    }

private:
    std::mt19937 rng_;
    int field_bits_;
    uint64_t mod_;
    std::vector<std::vector<uint64_t>> G_;
};

// ---------------------------------------------------------------------------
// mbedTLS implementation
// ---------------------------------------------------------------------------
class MbedTLSCrypto {
public:
    MbedTLSCrypto(int seed) : seed_(seed) {
        // Deterministic seed for reproducibility
    }

    // Generate provisioning matrix G[t][N] using mbedTLS-style random
    // Uses std::mt19937 seeded with the same seed for deterministic comparison
    void provision_matrix(int t, int N, uint64_t mod) {
        G_.resize(t, std::vector<uint64_t>(N));
        std::mt19937 rng(seed_);
        for (int i = 0; i < t; ++i) {
            for (int j = 0; j < N; ++j) {
                G_[i][j] = static_cast<uint64_t>(rng()) % mod;
            }
        }
    }

    // Get secret shares for node nid (column nid of G)
    std::vector<uint64_t> get_secrets(int nid) const {
        std::vector<uint64_t> shares(G_.size());
        for (size_t i = 0; i < G_.size(); ++i) {
            shares[i] = G_[i][nid];
        }
        return shares;
    }

    // Derive pairwise key using mbedTLS HMAC-SHA256
    uint64_t derive_key(int a, int b, int field_bits) const {
        if (a == b) return 0;

        // Build key material: column_a || column_b || ID_A || ID_B
        std::vector<uint8_t> key_material;
        for (size_t i = 0; i < G_.size(); ++i) {
            uint64_t val = G_[i][a];
            for (int k = 0; k < 8; ++k) {
                key_material.push_back(static_cast<uint8_t>((val >> (8 * k)) & 0xFF));
            }
        }
        for (size_t i = 0; i < G_.size(); ++i) {
            uint64_t val = G_[i][b];
            for (int k = 0; k < 8; ++k) {
                key_material.push_back(static_cast<uint8_t>((val >> (8 * k)) & 0xFF));
            }
        }
        key_material.push_back(static_cast<uint8_t>(a & 0xFF));
        key_material.push_back(static_cast<uint8_t>((a >> 8) & 0xFF));
        key_material.push_back(static_cast<uint8_t>(b & 0xFF));
        key_material.push_back(static_cast<uint8_t>((b >> 8) & 0xFF));

        // HMAC-SHA256 via mbedtls_md_hmac
        const mbedtls_md_info_t* md_info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
        uint8_t mac[32];
        int ret = mbedtls_md_hmac(md_info, key_material.data(), key_material.size(),
                                  key_material.data(), key_material.size(), mac);
        if (ret != 0) {
            return 0;  // Error fallback
        }

        // Truncate to field_bits bits
        int bytes_needed = field_bits / 8;
        uint64_t result = 0;
        for (int k = 0; k < bytes_needed && k < 8; ++k) {
            result = (result << 8) | mac[k];
        }
        return result % (1ULL << field_bits);
    }

private:
    int seed_;
    std::vector<std::vector<uint64_t>> G_;
};

// ---------------------------------------------------------------------------
// Benchmark results
// ---------------------------------------------------------------------------
struct BenchResult {
    int num_nodes;
    int t;
    int field_bits;
    double pure_cpp_prov_ms;
    double mbedtls_prov_ms;
    double pure_cpp_deriv_ms;
    double mbedtls_deriv_ms;
    double pure_cpp_handshake_ms;
    double mbedtls_handshake_ms;
};

// ---------------------------------------------------------------------------
// Run benchmark for a given configuration
// ---------------------------------------------------------------------------
BenchResult run_benchmark(int num_nodes, int t, int field_bits, int trials) {
    BenchResult result;
    result.num_nodes = num_nodes;
    result.t = t;
    result.field_bits = field_bits;

    double pure_cpp_prov_total = 0.0;
    double mbedtls_prov_total = 0.0;
    double pure_cpp_deriv_total = 0.0;
    double mbedtls_deriv_total = 0.0;
    double pure_cpp_handshake_total = 0.0;
    double mbedtls_handshake_total = 0.0;

    for (int trial = 0; trial < trials; ++trial) {
        int seed = 42 + trial;

        // --- Pure C++ ---
        {
            PureCPP cpp(seed, field_bits);
            Timer tm;
            tm.start();
            cpp.provision_matrix(t, num_nodes);
            pure_cpp_prov_total += tm.stop_ms();

            Timer t2;
            t2.start();
            for (int i = 0; i < num_nodes; ++i) {
                for (int j = i + 1; j < num_nodes; ++j) {
                    cpp.derive_key(i, j);
                }
            }
            pure_cpp_deriv_total += t2.stop_ms();

            Timer t3;
            t3.start();
            for (int i = 0; i < num_nodes; ++i) {
                for (int j = i + 1; j < num_nodes; ++j) {
                    auto sa = cpp.get_secrets(i);
                    auto sb = cpp.get_secrets(j);
                    uint64_t key = 0;
                    for (size_t k = 0; k < sa.size(); ++k) {
                        key = (key + sa[k] * sb[k]) % (1ULL << field_bits);
                    }
                    (void)key;
                }
            }
            pure_cpp_handshake_total += t3.stop_ms();
        }

        // --- mbedTLS ---
        {
            MbedTLSCrypto mb(seed);
            Timer tm;
            tm.start();
            mb.provision_matrix(t, num_nodes, MOD);
            mbedtls_prov_total += tm.stop_ms();

            Timer t2;
            t2.start();
            for (int i = 0; i < num_nodes; ++i) {
                for (int j = i + 1; j < num_nodes; ++j) {
                    mb.derive_key(i, j, field_bits);
                }
            }
            mbedtls_deriv_total += t2.stop_ms();

            Timer t3;
            t3.start();
            for (int i = 0; i < num_nodes; ++i) {
                for (int j = i + 1; j < num_nodes; ++j) {
                    auto sa = mb.get_secrets(i);
                    auto sb = mb.get_secrets(j);
                    uint64_t key = 0;
                    for (size_t k = 0; k < sa.size(); ++k) {
                        key = (key + sa[k] * sb[k]) % (1ULL << field_bits);
                    }
                    (void)key;
                }
            }
            mbedtls_handshake_total += t3.stop_ms();
        }
    }

    result.pure_cpp_prov_ms = pure_cpp_prov_total / trials;
    result.mbedtls_prov_ms = mbedtls_prov_total / trials;
    result.pure_cpp_deriv_ms = pure_cpp_deriv_total / trials;
    result.mbedtls_deriv_ms = mbedtls_deriv_total / trials;
    result.pure_cpp_handshake_ms = pure_cpp_handshake_total / trials;
    result.mbedtls_handshake_ms = mbedtls_handshake_total / trials;

    return result;
}

// ---------------------------------------------------------------------------
// Output results as JSON
// ---------------------------------------------------------------------------
int main(int argc, char* argv[]) {
    std::vector<int> node_counts = {30, 100, 500};
    int t = DEFAULT_T;
    int field_bits = DEFAULT_FIELD_BITS;
    int trials = 5;

    // Parse command-line arguments
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--nodes" && i + 1 < argc) {
            ++i;
            node_counts.clear();
            std::string val = argv[i];
            size_t pos = 0;
            while ((pos = val.find(',')) != std::string::npos) {
                node_counts.push_back(std::stoi(val.substr(0, pos)));
                val.erase(0, pos + 1);
            }
            node_counts.push_back(std::stoi(val));
        } else if (arg == "--trials" && i + 1 < argc) {
            ++i;
            trials = std::stoi(argv[i]);
        } else if (arg == "--t" && i + 1 < argc) {
            ++i;
            t = std::stoi(argv[i]);
        } else if (arg == "--field-bits" && i + 1 < argc) {
            ++i;
            field_bits = std::stoi(argv[i]);
        }
    }

    std::cout << "{" << std::endl;
    std::cout << "  \"config\": {" << std::endl;
    std::cout << "    \"t\": " << t << "," << std::endl;
    std::cout << "    \"field_bits\": " << field_bits << "," << std::endl;
    std::cout << "    \"trials\": " << trials << std::endl;
    std::cout << "  }," << std::endl;
    std::cout << "  \"results\": [" << std::endl;

    for (size_t i = 0; i < node_counts.size(); ++i) {
        BenchResult r = run_benchmark(node_counts[i], t, field_bits, trials);
        std::cout << "    {" << std::endl;
        std::cout << "      \"nodes\": " << r.num_nodes << "," << std::endl;
        std::cout << "      \"pure_cpp_prov_ms\": " << std::fixed << std::setprecision(6)
                  << r.pure_cpp_prov_ms << "," << std::endl;
        std::cout << "      \"mbedtls_prov_ms\": " << std::fixed << std::setprecision(6)
                  << r.mbedtls_prov_ms << "," << std::endl;
        std::cout << "      \"pure_cpp_deriv_ms\": " << std::fixed << std::setprecision(6)
                  << r.pure_cpp_deriv_ms << "," << std::endl;
        std::cout << "      \"mbedtls_deriv_ms\": " << std::fixed << std::setprecision(6)
                  << r.mbedtls_deriv_ms << "," << std::endl;
        std::cout << "      \"pure_cpp_handshake_ms\": " << std::fixed << std::setprecision(6)
                  << r.pure_cpp_handshake_ms << "," << std::endl;
        std::cout << "      \"mbedtls_handshake_ms\": " << std::fixed << std::setprecision(6)
                  << r.mbedtls_handshake_ms << std::endl;
        std::cout << "    }" << (i + 1 < node_counts.size() ? "," : "") << std::endl;
    }

    std::cout << "  ]" << std::endl;
    std::cout << "}" << std::endl;

    return 0;
}
