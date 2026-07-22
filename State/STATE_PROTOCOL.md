# State Engine Protocol

This document defines the normative rule for the `state-hello-v1` deterministic state transition.

## Input

- **Prior State Vector**
- **Observation Feed**
- **Transition Specification**

## Output

- **State Transition Artifact** (which contains the `next_state`)

## Evaluation Order

1. Validate prior state, observation feed, and transition specification schemas.
2. Canonically hash all three inputs to produce `prior_state_root`, `observation_feed_root`, and `transition_spec_root`.
3. Reject duplicate IDs within the observation feed.
4. Select observations matching `transition_spec.subject`.
5. Skip observations already recorded in `prior_state.applied_observation_ids`.
6. For each unseen observation with `support == 1`:
   - Add `transition_spec.supported_increment` to `evidence_count`.
7. For `support == 0`:
   - Record it as applied without changing `evidence_count`.
8. For `support == -1`:
   - Record it as applied without changing `evidence_count` and emit a `CONTRADICTION_OBSERVED` reason code.
9. Clamp `evidence_count` at the canonical safe-integer maximum (`9007199254740991`). If clamped, emit an `EVIDENCE_COUNT_CLAMPED` reason code.
10. Sort `applied_observation_ids` lexically.
11. Sort all collected `reason_codes` lexically.
12. Emit a new state and transition artifact.
13. Never mutate any input.
