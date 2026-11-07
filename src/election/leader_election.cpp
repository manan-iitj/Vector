#include "election/leader_election.h"
#include <iostream>
#include <algorithm>

namespace haven {

LeaderElection::LeaderElection()
    : claiming_state_{false, 0, 0, 0} {}

LeaderElection::~LeaderElection() {}

ElectionResult LeaderElection::run_election(
    std::shared_ptr<Node> initiator,
    std::vector<std::shared_ptr<Node>>& all_nodes) {

    ElectionResult result;
    if (!initiator || all_nodes.empty()) {
        std::cout << "[WARN] " << "Cannot run election: missing initiator or nodes" << std::endl;
        return result;
    }

    std::cout << "Running leader election initiated by node " << initiator->get_id().id << std::endl;

    CandidateManager mgr;

    int64_t epoch_id = 0;

    // Start election epoch
    if (!mgr.start_election_epoch(initiator, epoch_id)) {
        std::cout << "[WARN] " << "Failed to start election epoch " << epoch_id << std::endl;
        return result;
    }

    // Register all nodes as candidates
    for (const auto& node : all_nodes) {
        mgr.register_candidate(node, epoch_id);
    }

    // Apply max-consensus
    if (!mgr.apply_max_consensus(all_nodes, epoch_id)) {
        std::cout << "[WARN] " << "Max-consensus failed for epoch " << epoch_id << std::endl;
        return result;
    }

    // Announce leader
    auto leader = mgr.announce_leader(epoch_id);
    if (leader) {
        leader->set_leader(true);
        result.success = true;
        result.new_leader = leader;
        result.epoch_id = epoch_id;
        std::cout << "Leader elected: node " << leader->get_id().id << std::endl;
    }

    // Update claiming state
    ClaimingState state = get_claiming_state();
    state.in_claiming = false;
    state.claiming_node_id = leader ? leader->get_id().id : 0;
    set_claiming_state(state);

    return result;
}

bool LeaderElection::detect_election_need(std::shared_ptr<Node> node) {
    if (!node) return false;
    // Placeholder: election needed if node believes leadership is stale
    (void)node;
    return false;
}

std::vector<CandidateScore> LeaderElection::generate_candidates(
    std::shared_ptr<Node> initiator,
    std::vector<std::shared_ptr<Node>>& all_nodes) {

    std::vector<CandidateScore> candidates;
    if (!initiator) return candidates;

    CandidateScore init_score;
    init_score.node_id = initiator->get_id().id;
    init_score.score = 0;
    init_score.residual_battery = initiator->get_residual_battery();
    init_score.suitability = 0;
    candidates.push_back(init_score);

    for (const auto& node : all_nodes) {
        if (node.get() == initiator.get()) continue;
        CandidateScore s;
        s.node_id = node->get_id().id;
        s.score = 0;
        s.residual_battery = node->get_residual_battery();
        s.suitability = 0;
        candidates.push_back(s);
    }

    return candidates;
}

bool LeaderElection::propagate_candidates(
    std::vector<std::shared_ptr<Node>>& all_nodes,
    CandidateManager& mgr) {

    if (all_nodes.empty()) return false;
    std::cout << "[DEBUG] " << "Propagating candidate information to " << all_nodes.size() << " nodes" << std::endl;
    (void)mgr;
    return true;
}

bool LeaderElection::apply_consensus(CandidateManager& mgr, int64_t epoch_id) {
    std::vector<std::shared_ptr<Node>> empty;
    return mgr.apply_max_consensus(empty, epoch_id);
}

bool LeaderElection::authenticate_claim(
    std::shared_ptr<Node> claimant, int64_t epoch_id) {

    CandidateManager mgr;
    return mgr.authenticate_claim(claimant, epoch_id);
}

std::shared_ptr<Node> LeaderElection::announce_leader(
    CandidateManager& mgr, int64_t epoch_id) {

    return mgr.announce_leader(epoch_id);
}

void LeaderElection::update_nodes_after_election(
    std::vector<std::shared_ptr<Node>>& all_nodes,
    std::shared_ptr<Node> new_leader) {

    for (auto& node : all_nodes) {
        node->set_leader(node.get() == new_leader.get());
    }
}

LeaderElection::ClaimingState LeaderElection::get_claiming_state() const {
    return claiming_state_;
}

void LeaderElection::set_claiming_state(LeaderElection::ClaimingState state) {
    claiming_state_ = state;
}

bool LeaderElection::check_self_claim(
    const std::vector<CandidateScore>& candidates,
    uint64_t node_id) {

    int self_claims = 0;
    for (const auto& c : candidates) {
        if (c.node_id == node_id) self_claims++;
    }
    return self_claims > 1;
}

}  // namespace haven
