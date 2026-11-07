#ifndef VECTOR_JOINING_PROTOCOL_H
#define VECTOR_JOINING_PROTOCOL_H

#include <string>
#include <vector>
#include <memory>
#include "network/node.h"
#include "security/crypto_manager.h"
#include "network/network_manager.h"
#include "clustering/heed.h"
#include "election/candidate_manager.h"

namespace haven {

struct JoinStatus {
    enum Enum {
        NEW_NODE,
        JOINING,
        AUTHENTICATED,
        MEMBER,
        REVOKED
    };
};

struct JoinRequest {
    uint64_t new_node_id;
    uint64_t requesting_node_id;
    std::vector<uint8_t> provisioning_material;  // keys, certificates, etc.
    int64_t timestamp;
};

class JoiningProtocol {
public:
    JoiningProtocol();
    ~JoiningProtocol();
    
    // Complete node joining sequence
    // NEW_NODE -> JOINING -> JOIN_REQUEST -> AUTHENTICATION -> JOIN_ACCEPT -> MEMBER
    bool process_join_request(const JoinRequest& request,
                               std::shared_ptr<Node> accepting_node,
                               NetworkManager& net_mgr,
                               CryptoManager& crypto);
    
    // Revoke a node's membership
    bool revoke_node(uint64_t node_id, NetworkManager& net_mgr);
    
    // Check if node is authorized
    bool is_authorized(uint64_t node_id, NetworkManager& net_mgr);
    
    // Get join status
    JoinStatus::Enum get_join_status(uint64_t node_id, NetworkManager& net_mgr);
    
private:
    // Verify authentication handshake
    bool verify_authentication(std::shared_ptr<Node> node,
                                CryptoManager& crypto,
                                const std::vector<uint8_t>& challenge);
    
    // Update routing after join
    bool update_routing_after_join(std::shared_ptr<Node> new_node,
                                    NetworkManager& net_mgr);
    
    // Reconsider clustering after join
    bool reconsider_clustering(std::shared_ptr<Node> new_node,
                               HEED& heed_alg,
                               NetworkManager& net_mgr);
    
    // Synchronize leader election state
    bool sync_leader_election(std::shared_ptr<Node> new_node,
                              CandidateManager& mgr,
                              NetworkManager& net_mgr);
};

}  // namespace haven

#endif // VECTOR_JOINING_PROTOCOL_H