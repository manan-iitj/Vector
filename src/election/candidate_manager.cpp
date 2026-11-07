#include "election/candidate_manager.h"
#include <iostream>
#include <algorithm>
#include <numeric>
#include <unordered_set>

namespace haven {

CandidateManager::CandidateManager()
    : current_epoch_(0), current_leader_(nullptr),
      battery_weight_(0.7), energy_decay_(0.95), min_candidates_(2) {}

CandidateManager::~CandidateManager() {}

bool CandidateManager::start_election_epoch(std::shared_ptr<Node> initiator, int64_t epoch_id) {
    if (!initiator) return false;
    
    std::lock_guard<std::mutex> lock(election_mutex_);
    
    // Check if an election is already in progress for a newer epoch
    if (epochs_.count(epoch_id) > 0) {
        std::cout << "[WARN] " << "Election epoch " << epoch_id << " already exists" << std::endl;
        // Check if it's newer than current
        if (epoch_id > current_epoch_) {
            // Allow newer election to supersede
        } else {
            return false;  // older election, reject
        }
    }
    
    ElectionEpoch epoch;
    epoch.epoch_id = epoch_id;
    epoch.start_time = 0.0;
    epoch.active = true;
    epoch.winner = nullptr;
    
    // Initialize with the initiator as first candidate
    CandidateScore init_score;
    init_score.node_id = initiator->get_id().id;
    init_score.score = compute_candidate_score(initiator);
    init_score.residual_battery = initiator->get_residual_battery();
    init_score.suitability = init_score.score;
    epoch.candidates.push_back(init_score);
    
    epochs_[epoch_id] = epoch;
    current_epoch_ = epoch_id;
    
    std::cout << "Started election epoch " << epoch_id 
        << " initiated by node " << initiator->get_id().id << std::endl;
    
    return true;
}

bool CandidateManager::register_candidate(std::shared_ptr<Node> candidate, int64_t epoch_id) {
    if (!candidate) return false;
    
    std::lock_guard<std::mutex> lock(election_mutex_);
    
    if (epochs_.find(epoch_id) == epochs_.end()) {
        std::cerr << "[ERROR] " << "Election epoch " << epoch_id << " does not exist" << std::endl;
        return false;
    }
    
    ElectionEpoch& epoch = epochs_.at(epoch_id);
    
    // Check if this node is already a candidate
    for (const auto& c : epoch.candidates) {
        if (c.node_id == candidate->get_id().id) {
            std::cout << "Node " << candidate->get_id().id 
                << " is already a candidate in epoch " << epoch_id << std::endl;
            return false;
        }
    }
    
    CandidateScore score;
    score.node_id = candidate->get_id().id;
    score.score = compute_candidate_score(candidate);
    score.residual_battery = candidate->get_residual_battery();
    score.suitability = score.score;
    
    epoch.candidates.push_back(score);
    
    std::cout << "Node " << candidate->get_id().id 
        << " registered as candidate in epoch " << epoch_id 
        << " with score " << score.score << std::endl;
    
    return true;
}

int64_t CandidateManager::compute_candidate_score(std::shared_ptr<Node> node) {
    if (!node) return 0;
    
    // Score considers: residual battery and possibly other factors
    // Normalized to 0-1000 range
    
    double residual = node->get_residual_battery();
    double max_possible = node->get_battery_capacity();
    
    if (max_possible <= 0) return 0;
    
    // Normalized battery component (0-1)
    double battery_norm = residual / max_possible;
    
    // Score = battery_weight * battery_norm * 1000
    // Higher battery = higher score (more suitable as leader)
    int64_t score = static_cast<int64_t>(battery_weight_ * battery_norm * 1000);
    
    return score;
}

void CandidateManager::normalize_scores(std::vector<CandidateScore>& candidates) {
    if (candidates.empty()) return;
    
    // Find min and max scores
    int64_t min_score = std::numeric_limits<int64_t>::max();
    int64_t max_score = std::numeric_limits<int64_t>::min();
    
    for (const auto& c : candidates) {
        min_score = std::min(min_score, c.score);
        max_score = std::max(max_score, c.score);
    }
    
    // If all scores are the same, no normalization needed
    if (min_score == max_score) return;
    
    // Normalize to 0-1 range, then scale to 0-1000
    for (auto& c : candidates) {
        if (max_score > min_score) {
            c.score = static_cast<int64_t>(
                (c.score - min_score) * 1000.0 / (max_score - min_score));
        } else {
            c.score = 500;  // default middle
        }
    }
}

bool CandidateManager::propagate_candidate(std::shared_ptr<Node> advertiser, 
                                           const CandidateScore& score,
                                           std::vector<std::shared_ptr<Node>>& all_nodes) {
    if (!advertiser || all_nodes.empty()) return false;
    
    std::cout << "[DEBUG] " << "Propagating candidate advertisement from node " 
        << advertiser->get_id().id << " with score " << score.score << std::endl;
    
    // Advertise to all other nodes
    for (auto& node : all_nodes) {
        if (node.get() == advertiser.get()) continue;
        
        // Node receives candidate advertisement
        // Update its knowledge of candidates
        // In a full implementation, this would involve message passing
        // For now, just log the propagation
    }
    
    return true;
}

bool CandidateManager::apply_max_consensus(std::vector<std::shared_ptr<Node>>& all_nodes,
                                            int64_t epoch_id) {
    std::lock_guard<std::mutex> lock(election_mutex_);
    
    if (epochs_.find(epoch_id) == epochs_.end()) {
        std::cerr << "[ERROR] " << "Election epoch " << epoch_id << " does not exist" << std::endl;
        return false;
    }
    
    ElectionEpoch& epoch = epochs_.at(epoch_id);
    
    if (epoch.candidates.empty()) {
        std::cerr << "[ERROR] " << "No candidates in epoch " << epoch_id << std::endl;
        return false;
    }
    
    // Find the candidate with the maximum score
    auto best = std::max_element(epoch.candidates.begin(), epoch.candidates.end(),
        [](const CandidateScore& a, const CandidateScore& b) {
            return a.score < b.score;
        });
    
    if (best == epoch.candidates.end()) {
        std::cerr << "[ERROR] " << "No best candidate found" << std::endl;
        return false;
    }
    
    int64_t winning_score = best->score;
    uint64_t winning_id = best->node_id;
    
    std::cout << "Max-consensus winner: node " << winning_id 
        << " with score " << winning_score << std::endl;
    
    // Check for ties: if multiple candidates have the same top score
    std::vector<uint64_t> tied_ids;
    for (const auto& c : epoch.candidates) {
        if (c.score == winning_score) {
            tied_ids.push_back(c.node_id);
        }
    }
    
    if (tied_ids.size() > 1) {
        // Resolve tie deterministically: highest node ID wins
        winning_id = *std::max_element(tied_ids.begin(), tied_ids.end());
        std::cout << "Tie resolved: winner is node " << winning_id << std::endl;
    }
    
    // Set the winner node object from the nodes list
    for (const auto& node : all_nodes) {
        if (node->get_id().id == winning_id) {
            epoch.winner = node;
            break;
        }
    }
    
    std::cout << "Max-consensus applied for epoch " << epoch_id 
        << ": winner node " << winning_id << std::endl;
    
    return true;
}

uint64_t CandidateManager::resolve_tie(const std::vector<CandidateScore>& tied_candidates) {
    if (tied_candidates.empty()) return 0;
    if (tied_candidates.size() == 1) return tied_candidates[0].node_id;
    
    // Deterministic tie-breaking: use node ID as tiebreaker
    // Higher node ID wins (or could use lower, as long as it's consistent)
    // Sort by node ID and pick the highest
    std::vector<CandidateScore> sorted = tied_candidates;
    std::sort(sorted.begin(), sorted.end(), 
        [](const CandidateScore& a, const CandidateScore& b) {
            return a.node_id > b.node_id;  // descending order
        });
    
    return sorted[0].node_id;
}

bool CandidateManager::authenticate_claim(std::shared_ptr<Node> claimant, 
                                          int64_t epoch_id) {
    if (!claimant) return false;
    
    std::lock_guard<std::mutex> lock(election_mutex_);
    
    if (epochs_.find(epoch_id) == epochs_.end()) {
        std::cerr << "[ERROR] " << "Election epoch " << epoch_id << " does not exist" << std::endl;
        return false;
    }
    
    // Verify that the claimant is actually a candidate in this epoch
    const ElectionEpoch& epoch = epochs_.at(epoch_id);
    bool is_candidate = false;
    for (const auto& c : epoch.candidates) {
        if (c.node_id == claimant->get_id().id) {
            is_candidate = true;
            break;
        }
    }
    
    if (!is_candidate) {
        std::cout << "[WARN] " << "Node " << claimant->get_id().id 
            << " is not a candidate in epoch " << epoch_id << std::endl;
        return false;
    }
    
    std::cout << "Claim authenticated: node " << claimant->get_id().id 
        << " is a verified candidate in epoch " << epoch_id << std::endl;
    
    return true;
}

std::shared_ptr<Node> CandidateManager::announce_leader(int64_t epoch_id) {
    std::lock_guard<std::mutex> lock(election_mutex_);
    
    if (epochs_.find(epoch_id) == epochs_.end()) {
        std::cerr << "[ERROR] " << "Election epoch " << epoch_id << " does not exist" << std::endl;
        return nullptr;
    }
    
    ElectionEpoch& epoch = epochs_.at(epoch_id);
    
    if (epoch.winner) {
        return epoch.winner;
    }

    std::cout << "[WARN] " << "No winner found for epoch " << epoch_id << std::endl;
    return nullptr;
}

int64_t CandidateManager::get_current_epoch() const {
    return current_epoch_;
}

std::shared_ptr<Node> CandidateManager::get_current_leader() const {
    return current_leader_;
}

bool CandidateManager::is_election_needed(std::shared_ptr<Node> node) {
    if (!node) return false;
    
    // Check conditions that trigger a new election:
    // - Current leader has failed
    // - Leader's battery is critically low
    // - Timer expired
    // - Network partition detected
    
    // Placeholder: return false
    // In full implementation, check leader status, timers, etc.
    return false;
}

}  // namespace haven