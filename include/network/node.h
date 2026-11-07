#ifndef VECTOR_NODE_H
#define VECTOR_NODE_H

#include <string>
#include <vector>
#include <map>
#include <mutex>
#include <atomic>
#include <cstdint>
#include <cmath>

namespace haven {

enum class NodeStatus {
    ACTIVE,
    SLEEPING,
    FAILED,
    RECOVERING,
    LEAVING
};

enum class NodeRole {
    MEMBER,
    CLUSTER_HEAD,
    LEADER,
    GATEWAY
};

enum class AuthStatus {
    UNAUTHENTICATED,
    AUTHENTICATING,
    AUTHENTICATED,
    REVOKED
};

struct WirelessNodeID {
    uint64_t id;
    std::string node_type;  // "drone", "iot", "gateway"

    WirelessNodeID() : id(0) {}
    WirelessNodeID(uint64_t id, const std::string& node_type)
        : id(id), node_type(node_type) {}

    bool operator==(const WirelessNodeID& other) const {
        return id == other.id;
    }
    bool operator<(const WirelessNodeID& other) const {
        return id < other.id;
    }
};

struct NodePosition {
    double x;
    double y;
    double z;  // altitude for drones

    NodePosition() : x(0), y(0), z(0) {}
    NodePosition(double x, double y, double z) : x(x), y(y), z(z) {}

    double distance_to(const NodePosition& other) const;
};

class Node {
public:
    Node(WirelessNodeID id, NodePosition position, double battery_capacity);
    ~Node();
    
    // Basic identity
    WirelessNodeID get_id() const;
    NodePosition get_position() const;
    double get_battery_capacity() const;
    double get_residual_battery() const;
    void set_residual_battery(double residual);
    
    // Status
    NodeStatus get_status() const;
    void set_status(NodeStatus status);
    AuthStatus get_auth_status() const;
    void set_auth_status(AuthStatus status);
    
    // Role
    NodeRole get_role() const;
    void set_role(NodeRole role);
    
    // Cluster
    uint32_t get_cluster_id() const;
    void set_cluster_id(uint32_t cluster_id);
    bool is_cluster_head() const;
    void set_cluster_head(bool is_head);
    
    // Leader
    bool is_leader() const;
    void set_leader(bool is_leader);
    
    // Election
    int64_t get_election_score() const;
    void set_election_score(int64_t score);
    int64_t get_epoch() const;
    void set_epoch(int64_t epoch);
    
    // Key material reference (opaque handle)
    uint64_t get_key_handle() const;
    void set_key_handle(uint64_t handle);
    
    // Neighbor management
    void add_neighbor(WirelessNodeID neighbor_id, double last_seen);
    void remove_neighbor(WirelessNodeID neighbor_id);
    std::vector<WirelessNodeID> get_neighbors() const;
    size_t neighbor_count() const;
    
    // Link status with specific node
    bool has_link_to(WirelessNodeID other) const;
    void set_link_to(WirelessNodeID other, bool connected);
    
    // Timestamps
    int64_t get_last_seen() const;
    void set_last_seen(int64_t timestamp);
    int64_t get_join_time() const;
    void set_join_time(int64_t timestamp);
    
    // Node ID string for logging
    std::string to_string() const;
    
private:
    WirelessNodeID node_id_;
    NodePosition position_;
    double battery_capacity_;
    double residual_battery_;
    NodeStatus status_;
    AuthStatus auth_status_;
    NodeRole role_;
    uint32_t cluster_id_;
    bool is_cluster_head_;
    bool is_leader_;
    int64_t election_score_;
    int64_t epoch_;
    uint64_t key_handle_;
    std::vector<WirelessNodeID> neighbors_;
    std::map<WirelessNodeID, bool> link_status_;
    int64_t last_seen_;
    int64_t join_time_;
};

}  // namespace haven

namespace std {
template <>
struct hash<haven::WirelessNodeID> {
    size_t operator()(const haven::WirelessNodeID& n) const noexcept {
        return std::hash<uint64_t>()(n.id);
    }
};

}  // namespace std

#endif // VECTOR_NODE_H