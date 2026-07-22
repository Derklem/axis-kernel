import json
import os
from datetime import datetime, timezone

LEDGER_PATH = r"D:\Infinite\Infinity\Strategy\Execution_Escrow\epistemic_theory_market_v2.jsonl"

def append_to_ledger(record):
    with open(LEDGER_PATH, 'a') as f:
        f.write(json.dumps(record) + "\n")

def initialize_market():
    if os.path.exists(LEDGER_PATH):
        print(f"Market ledger already exists at {LEDGER_PATH}. Aborting initialization to prevent overwrite.")
        return

    timestamp = datetime.now(timezone.utc).isoformat() + "Z"

    # Base mechanical parameters for all theories
    base_params = {
        "timestamp_utc": timestamp,
        "confidence_score": 0.3333,
        "accumulated_weight": 1.0,
        "observation_count": 0,
        "unknown_dominant_streak": 0,
        "disconfirming_events_required": 3,
        "evaluation_window_days": 180,
        "evidence_weighting": "time_decay",
        "retirement_threshold": 0.30,
        "min_observations_before_retirement": 5,
        "min_total_group_weight_before_retirement": 10.0,
        "status": "ACTIVE",
        "history": []
    }

    # Group 1
    g1_t1 = {"theory_group_id": "G1", "theory_id": "T1", "statement": "Independent cognition layers exposed to the architecture will exhibit convergence above baseline rates."}
    g1_t1a = {"theory_group_id": "G1", "theory_id": "T1A", "statement": "Convergence is an artifact of conversational context and will degrade as the system scales across isolated, non-overlapping contexts."}
    g1_t1u = {"theory_group_id": "G1", "theory_id": "T1U", "statement": "Neither T1 nor T1A currently explains the observed variance in convergence."}

    # Group 2
    g2_t2 = {"theory_group_id": "G2", "theory_id": "T2", "statement": "Mechanisms that improve telemetry accuracy will causally outperform mechanisms that optimize for compliance without improving telemetry accuracy."}
    g2_t2a = {"theory_group_id": "G2", "theory_id": "T2A", "statement": "Systems that enforce strict structural compliance will outperform systems that prioritize raw telemetry accuracy at the expense of strict structural constraint."}
    g2_t2u = {"theory_group_id": "G2", "theory_id": "T2U", "statement": "Neither T2 nor T2A currently explains performance differentials."}

    # Group 3
    g3_t3 = {"theory_group_id": "G3", "theory_id": "T3", "statement": "Lexical priority overrides exist only when empirical failure is proven to be structurally terminal and mathematically unrecoverable."}
    g3_t3a = {"theory_group_id": "G3", "theory_id": "T3A", "statement": "Over time, the definition of terminal risk will systematically inflate to capture more subsystems, turning lexical priority into a tool for bureaucratic override."}
    g3_t3u = {"theory_group_id": "G3", "theory_id": "T3U", "statement": "Neither T3 nor T3A adequately models the boundary behavior of catastrophe classification."}

    # Group 4
    g4_t4 = {"theory_group_id": "G4", "theory_id": "T4", "statement": "The architecture forms a model-independent epistemic attractor."}
    g4_t4a = {"theory_group_id": "G4", "theory_id": "T4A", "statement": "The architecture appears model-independent only because the tests are sampling a narrow region of cognition space."}
    g4_t4u = {"theory_group_id": "G4", "theory_id": "T4U", "statement": "The nature of the attractor is currently unexplainable by either hypothesis."}

    theories = [g1_t1, g1_t1a, g1_t1u, g2_t2, g2_t2a, g2_t2u, g3_t3, g3_t3a, g3_t3u, g4_t4, g4_t4a, g4_t4u]

    for t in theories:
        record = {**t, **base_params}
        append_to_ledger(record)
    
    print(f"Successfully initialized Epistemic Theory Market v2 with 4 groups (12 theories) at {LEDGER_PATH}.")

if __name__ == "__main__":
    initialize_market()
