#include "network/node.h"
#include <cmath>
#include <sstream>

namespace haven {

double NodePosition::distance_to(const NodePosition& other) const {
    double dx = x - other.x;
    double dy = y - other.y;
    double dz = z - other.z;
    return std::sqrt(dx * dx + dy * dy + dz * dz);
}

Node::Node(WirelessNodeID id, NodePosition position, double battery_capacity)
    : node_id_(id),
      position_(position),
      battery_capacity_(battery_capacity),
      residual_battery_(battery_capacity),
      status_(NodeStatus::ACTIVE),
      auth_status_(AuthStatus::UNAUTHENTICATED),
      role_(NodeRole::MEMBER),
      cluster_id_(0),
      is_cluster_head_(false),
      is_leader_(false),
      election_score_(0),
      epoch_(0),
      key_handle_(0),
      last_seen_(0),
      join_time_(0)
{
}

Node::~Node() {}

WirelessNodeID Node::get_id() const { return node_id_; }

NodePosition Node::get_position() const { return position_; }

double Node::get_battery_capacity() const { return battery_capacity_; }

double Node::get_residual_battery() const { return residual_battery_; }

void Node::set_residual_battery(double residual) { residual_battery_ = residual; }

NodeStatus Node::get_status() const { return status_; }

void Node::set_status(NodeStatus status) { status_ = status; }

AuthStatus Node::get_auth_status() const { return auth_status_; }

void Node::set_auth_status(AuthStatus status) { auth_status_ = status; }

NodeRole Node::get_role() const { return role_; }

void Node::set_role(NodeRole role) { role_ = role; }

uint32_t Node::get_cluster_id() const { return cluster_id_; }

void Node::set_cluster_id(uint32_t cluster_id) { cluster_id_ = cluster_id; }

bool Node::is_cluster_head() const { return is_cluster_head_; }

void Node::set_cluster_head(bool is_head) { is_cluster_head_ = is_head; }

bool Node::is_leader() const { return is_leader_; }

void Node::set_leader(bool is_leader) { is_leader_ = is_leader; }

int64_t Node::get_election_score() const { return election_score_; }

void Node::set_election_score(int64_t score) { election_score_ = score; }

int64_t Node::get_epoch() const { return epoch_; }

void Node::set_epoch(int64_t epoch) { epoch_ = epoch; }

uint64_t Node::get_key_handle() const { return key_handle_; }

void Node::set_key_handle(uint64_t handle) { key_handle_ = handle; }

void Node::add_neighbor(WirelessNodeID neighbor_id, double last_seen) {
    neighbors_.push_back(neighbor_id);
    // Also update link status
    link_status_[neighbor_id] = true;
}

void Node::remove_neighbor(WirelessNodeID neighbor_id) {
    neighbors_.erase(
        std::remove(neighbors_.begin(), neighbors_.end(), neighbor_id),
        neighbors_.end());
    link_status_.erase(neighbor_id);
}

std::vector<WirelessNodeID> Node::get_neighbors() const { return neighbors_; }

size_t Node::neighbor_count() const { return neighbors_.size(); }

bool Node::has_link_to(WirelessNodeID other) const {
    return link_status_.count(other) > 0 && link_status_.at(other);
}

void Node::set_link_to(WirelessNodeID other, bool connected) {
    link_status_[other] = connected;
}

int64_t Node::get_last_seen() const { return last_seen_; }

void Node::set_last_seen(int64_t timestamp) { last_seen_ = timestamp; }

int64_t Node::get_join_time() const { return join_time_; }

void Node::set_join_time(int64_t timestamp) { join_time_ = timestamp; }

std::string Node::to_string() const {
    std::ostringstream oss;
    oss << "Node(id=" << node_id_.id 
        << ", pos=(" << position_.x << "," << position_.y << "," << position_.z << ")"
        << ", battery=" << residual_battery_
        << ", status=" << static_cast<int>(status_)
        << ", auth=" << static_cast<int>(auth_status_)
        << ", role=" << static_cast<int>(role_)
        << ")";
    return oss.str();
}
}  // namespace haven