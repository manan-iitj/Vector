
#include "security/crypto_manager.h"
#include <iostream>
#include <chrono>
#include <vector>
#include <cstring>
#include <iomanip>

using namespace haven;
using namespace std::chrono;

int main() {
    CryptoManager crypto;
    crypto.initialize();

    // Test message sizes
    size_t sizes[] = {64, 256, 1024, 4096, 16384, 65536, 262144};
    int trials = 100;

    for (size_t sz : sizes) {
        std::vector<uint8_t> data(sz, 0xAB);
        std::vector<uint8_t> key(32, 0xCD);

        // SHA-256 timing
        auto t0 = high_resolution_clock::now();
        for (int i = 0; i < trials; i++) {
            auto h = crypto.compute_sha256(data);
        }
        auto t1 = high_resolution_clock::now();
        double sha_ms = duration_cast<microseconds>(t1 - t0).count() / trials / 1000.0;

        // HMAC-SHA256 timing
        t0 = high_resolution_clock::now();
        for (int i = 0; i < trials; i++) {
            auto h = crypto.compute_hmac_sha256(key, data);
        }
        t1 = high_resolution_clock::now();
        double hmac_ms = duration_cast<microseconds>(t1 - t0).count() / trials / 1000.0;

        std::cout << sz << " " << sha_ms << " " << hmac_ms << std::endl;
    }

    crypto.cleanup();
    return 0;
}
