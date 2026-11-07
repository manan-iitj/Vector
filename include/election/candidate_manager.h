#ifndef VECTOR_CANDIDATE_MANAGER_H
#define VECTOR_CANDIDATE_MANAGER_H

#include <string>
#include <vector>
#include <map>
#include <mutex>
#include <memory>
#include <cstdint>
#include "network/node.h"

namespace haven {

struct CandidateScore {
    uint64_t node_id;
    int64_t score;       // normalized candidate score
    double residual_battery;
    double energy_normalized;
    double suitability;  // combined suitability metric
    
    CandidateScore() : node_id(0), score(0), residual_battery(0), 
                       energy_normalized(0), suitability(0) {}
};

struct ElectionEpoch {
    int64_t epoch_id;
    int64_t start_time;
    int64_t end_time;
    bool active;
    std::vector<CandidateScore> candidates;
    std::shared_ptr<Node> winner;
    
    ElectionEpoch() : epoch_id(0), start_time(0), end_time(0), active(false) {}
};

class CandidateManager {
public:
    CandidateManager();
    ~CandidateManager();
    
    // Start a new election epoch
    bool start_election_epoch(std::shared_ptr<Node> initiator, int64_t epoch_id);
    
    // Register a candidate
    bool register_candidate(std::shared_ptr<Node> candidate, int64_t epoch_id);
    
    // Get all candidates for an epoch
    std::vector<CandidateScore> get_candidates(int64_t epoch_id) const;
    
    // Compute candidate score based on node suitability
    int64_t compute_candidate_score(std::shared_ptr<Node> node);
    
    // Normalize scores across all candidates
    void normalize_scores(std::vector<CandidateScore>& candidates);
    
    // Propagate candidate information across network
    bool propagate_candidate(std::shared_ptr<Node> advertiser, 
                             const CandidateScore& score,
                             std::vector<std::shared_ptr<Node>>& all_nodes);
    
    // Apply max-consensus: all nodes agree on the same winner
    bool apply_max_consensus(std::vector<std::shared_ptr<Node>>& all_nodes,
                              int64_t epoch_id);
    
    // Resolve ties deterministically
    uint64_t resolve_tie(const std::vector<CandidateScore>& tied_candidates);
    
    // Authenticate winning claim
    bool authenticate_claim(std::shared_ptr<Node> claimant, 
                           int64_t epoch_id);
    
    // Announce new leader
    std::shared_ptr<Node> announce_leader(int64_t epoch_id);
    
    // Get current epoch and leader
    int64_t get_current_epoch() const;
    std::shared_ptr<Node> get_current_leader() const;
    
    // Check if election is needed
    bool is_election_needed(std::shared_ptr<Node> node);
    
private:
    std::mutex election_mutex_;
    std::map<int64_t, ElectionEpoch> epochs_;
    int64_t current_epoch_;
    std::shared_ptr<Node> current_leader_;
    
    // Configurable scoring parameters
    double battery_weight_;      // weight for residual battery (0-1)
    double energy_decay_;        // exponential decay factor for battery
    int64_t min_candidates_;     // minimum candidates for election
};

}  // namespace haven

#endif // VECTOR_CANDIDATE_MANAGER_H