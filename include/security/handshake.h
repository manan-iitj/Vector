#ifndef VECTOR_HANDSHAKE_H
#define VECTOR_HANDSHAKE_H

#include <string>
#include <vector>
#include <cstdint>
#include <memory>
#include "crypto_manager.h"

namespace haven {

struct AuthMessage1 {
    uint64_t id_a;
    uint64_t id_b;
    std::vector<uint8_t> nonce_a;  // 16 bytes
    uint8_t protocol_version;
    
    AuthMessage1() : id_a(0), id_b(0), protocol_version(1) {}
};

struct AuthMessage2 {
    uint64_t id_a;
    uint64_t id_b;
    std::vector<uint8_t> nonce_b;  // 16 bytes
    std::vector<uint8_t> mac;      // HMAC(K_AB, N_A || N_B || ID_A || ID_B), 32 bytes
    
    AuthMessage2() : id_a(0), id_b(0) {}
};

struct AuthMessage3 {
    uint64_t id_a;
    uint64_t id_b;
    std::vector<uint8_t> mac;      // HMAC(K_AB, N_B || N_A || ID_A || ID_B), 32 bytes
    
    AuthMessage3() : id_a(0), id_b(0) {}
};

class Handshake {
public:
    Handshake();
    ~Handshake();
    
    // Initiate handshake: send message 1
    AuthMessage1 initiate(uint64_t my_id, uint64_t peer_id, CryptoManager& crypto);
    
    // Process message 2: receive from peer
    bool process_message2(const AuthMessage1& msg1, 
                          const AuthMessage2& msg2, CryptoManager& crypto);
    
    // Process message 3: send to peer
    AuthMessage3 generate_message3(const AuthMessage1& msg1, 
                                   const AuthMessage2& msg2, CryptoManager& crypto);
    
    // Verify completed handshake
    bool verify_handshake(const AuthMessage1& msg1,
                          const AuthMessage2& msg2,
                          const AuthMessage3& msg3, CryptoManager& crypto);
    
    // Extract derived session key
    std::vector<uint8_t> get_session_key() const;
    
    // Authentication state
    bool is_authenticated() const { return authenticated_; }
    uint64_t get_my_id() const { return my_id_; }
    uint64_t get_peer_id() const { return peer_id_; }
    
private:
    uint64_t my_id_;
    uint64_t peer_id_;
    bool authenticated_;
    
    // Session key derived from K_AB
    std::vector<uint8_t> session_key_;
    
    // Nonces
    std::vector<uint8_t> nonce_a_;
    std::vector<uint8_t> nonce_b_;
    
    // Message authentication
    bool verify_mac(const std::vector<uint8_t>& expected, 
                    const std::vector<uint8_t>& actual, CryptoManager& crypto);
    
    // Encode message for MAC computation
    std::vector<uint8_t> encode_mac_input(const AuthMessage1& msg1);
    std::vector<uint8_t> encode_mac_input(const AuthMessage2& msg2);
    std::vector<uint8_t> encode_mac_input(const AuthMessage3& msg3);
};

}  // namespace haven

#endif // VECTOR_HANDSHAKE_H