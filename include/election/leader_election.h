#ifndef VECTOR_LEADER_ELECTION_H
#define VECTOR_LEADER_ELECTION_H

#include <string>
#include <vector>
#include <memory>
#include "network/node.h"
#include "candidate_manager.h"

namespace haven {

struct ElectionResult {
    bool success;
    std::shared_ptr<Node> new_leader;
    int64_t epoch_id;
    bool tie_broken;
    std::string tie_break_reason;
    
    ElectionResult() : success(false), new_leader(nullptr), epoch_id(0), 
                       tie_broken(false) {}
};

class LeaderElection {
public:
    LeaderElection();
    ~LeaderElection();
    
    // Full election sequence
    ElectionResult run_election(std::shared_ptr<Node> initiator,
                                 std::vector<std::shared_ptr<Node>>& all_nodes);
    
    // Detect need for election
    bool detect_election_need(std::shared_ptr<Node> node);
    
    // Generate eligible candidates
    std::vector<CandidateScore> generate_candidates(std::shared_ptr<Node> initiator,
                                                    std::vector<std::shared_ptr<Node>>& all_nodes);
    
    // Propagate candidate information
    bool propagate_candidates(std::vector<std::shared_ptr<Node>>& all_nodes,
                               CandidateManager& mgr);
    
    // Apply distributed max-consensus
    bool apply_consensus(CandidateManager& mgr, int64_t epoch_id);
    
    // Authenticate winning claim
    bool authenticate_claim(std::shared_ptr<Node> claimant, int64_t epoch_id);
    
    // Announce new leader
    std::shared_ptr<Node> announce_leader(CandidateManager& mgr, int64_t epoch_id);
    
    // Update all participating nodes
    void update_nodes_after_election(std::vector<std::shared_ptr<Node>>& all_nodes,
                                      std::shared_ptr<Node> new_leader);
    
    // Orange CLAIMING state management
    struct ClaimingState {
        bool in_claiming;
        uint64_t claiming_node_id;
        int64_t timeout;
        int retry_count;
    };
    
    ClaimingState get_claiming_state() const;
    void set_claiming_state(ClaimingState state);
    
private:
    ClaimingState claiming_state_;
    
    // Prevent node from becoming leader if it only received its own advertisement
    bool check_self_claim(const std::vector<CandidateScore>& candidates, 
                          uint64_t node_id);
};

}  // namespace haven

#endif // VECTOR_LEADER_ELECTION_H