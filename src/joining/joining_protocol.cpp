#include "joining/joining_protocol.h"
#include <iostream>
#include <algorithm>
#include <unordered_set>

namespace haven {

JoiningProtocol::JoiningProtocol() {}

JoiningProtocol::~JoiningProtocol() {}

bool JoiningProtocol::process_join_request(const JoinRequest& request,
                                            std::shared_ptr<Node> accepting_node,
                                            NetworkManager& net_mgr,
                                            CryptoManager& crypto) {
    if (!accepting_node) {
        std::cerr << "[ERROR] " << "No accepting node specified" << std::endl;
        return false;
    }
    
    uint64_t new_node_id = request.new_node_id;
    
    std::cout << "Processing join request from ID " << request.requesting_node_id
        << " to node " << accepting_node->get_id().id << std::endl;
    
    // Step 1: NEW_NODE check - verify node is not already in network
    if (net_mgr.get_node(WirelessNodeID{new_node_id, ""}) != nullptr) {
        std::cout << "[WARN] " << "Node " << new_node_id << " already exists in network" << std::endl;
        return false;  // Duplicate ID rejection
    }
    
    // Step 2: JOINING - mark node as joining
    // Create new node entry
    NodePosition pos;  // position will be assigned later
    WirelessNodeID new_id{new_node_id, "node"};
    
    // Set initial status
    // net_mgr.add_node(new_id, pos, request.provisioning_material.size() > 0 ? 100.0 : 0.0);
    
    // For now, just check if the requesting node is authorized
    auto requester = net_mgr.get_node(WirelessNodeID{request.requesting_node_id, ""});
    if (!requester) {
        std::cerr << "[ERROR] " << "Requesting node " << request.requesting_node_id << " not found" << std::endl;
        return false;
    }
    
    // Step 3: AUTHENTICATION - run three-message handshake
    // In a full implementation, this would involve the nonce-based handshake
    // using the pairwise key derived from TurboBlom
    
    // Simplified: check if requesting node has valid key material
    // and can authenticate with the accepting node
    
    bool auth_success = false;
    
    // Check TurboBlom key derivation between requester and accepting node
    if (crypto.initialize()) {
        PairwiseKey key;
        bool derived = crypto.derive_pairwise_key(
            requester->get_id().id, 
            accepting_node->get_id().id, key);
        
        if (derived) {
            // Verify the derived key
            PairwiseKey key2;
            bool derived_back = crypto.derive_pairwise_key(
                accepting_node->get_id().id,
                requester->get_id().id, key2);
            
            if (derived_back) {
                // Check key agreement
                bool keys_match = true;
                for (size_t i = 0; i < key.key_material.size(); i++) {
                    if (key.key_material[i] != key2.key_material[i]) {
                        keys_match = false;
                        break;
                    }
                }
                
                if (keys_match) {
                    auth_success = true;
                    std::cout << "Authentication successful for node " << new_node_id << std::endl;
                } else {
                    std::cout << "[WARN] " << "Key disagreement during authentication" << std::endl;
                }
            }
        }
    }
    
    if (!auth_success) {
        std::cout << "[WARN] " << "Authentication failed for node " << new_node_id << std::endl;
        return false;
    }
    
    // Step 4: JOIN_ACCEPT - node is now a member
    // Add the new node to the network
    auto new_node = net_mgr.add_node(new_id, pos, 100.0);
    if (!new_node) {
        std::cerr << "[ERROR] " << "Failed to add new node to network" << std::endl;
        return false;
    }
    
    // Discover neighbors
    net_mgr.discover_neighbors(new_node);
    
    // Update routing tables
    net_mgr.update_neighbor_list(new_node);
    
    // Reconsider clustering
    // (would call heed.reconsider_clustering if HEED enabled)
    
    // Synchronize leader election
    // (would re-sync election state)
    
    std::cout << "Node " << new_node_id << " successfully joined as MEMBER" << std::endl;
    
    // Step 5: MEMBER - node is now fully integrated
    return true;
}

bool JoiningProtocol::revoke_node(uint64_t node_id, NetworkManager& net_mgr) {
    auto node = net_mgr.get_node(WirelessNodeID{node_id, ""});
    if (!node) {
        std::cout << "[WARN] " << "Node " << node_id << " not found in network" << std::endl;
        return false;
    }
    
    std::cout << "Revoking node " << node_id << std::endl;
    
    // Disconnect all links
    net_mgr.node_leave(node);
    
    // Clear key material
    // (would securely wipe TurboBlom key handles)
    
    // Reconsider clustering
    // Re-run HEED if enabled
    
    // Re-sync leader election
    // Re-run max-consensus if leader was revoked
    
    return true;
}

bool JoiningProtocol::is_authorized(uint64_t node_id, NetworkManager& net_mgr) {
    auto node = net_mgr.get_node(WirelessNodeID{node_id, ""});
    if (!node) return false;
    
    return node->get_auth_status() == AuthStatus::AUTHENTICATED;
}

JoinStatus::Enum JoiningProtocol::get_join_status(uint64_t node_id, NetworkManager& net_mgr) {
    auto node = net_mgr.get_node(WirelessNodeID{node_id, ""});
    if (!node) return JoinStatus::NEW_NODE;
    
    switch (node->get_auth_status()) {
        case AuthStatus::UNAUTHENTICATED:
            return JoinStatus::JOINING;
        case AuthStatus::AUTHENTICATED:
            return JoinStatus::MEMBER;
        case AuthStatus::REVOKED:
            return JoinStatus::REVOKED;
        default:
            return JoinStatus::NEW_NODE;
    }
}

}  // namespace haven