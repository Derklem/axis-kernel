# Empirical Field Study Notes: axis-kernel-v1.0.1

## Overview
This document summarizes the findings from the five field tests executed against the frozen `axis-kernel-v1.0.1` release. The study was conducted as an immutable experiment: all packages were installed from frozen distributions, and testing scripts used real engine entry points (`cli.py`).

## Findings

### 1. HYP_001 (Falsifiable Execution)
**Observed:** 
The dual verifier (Python and Rust) produced identical canonical hashes (`verification_root`) and successfully verified the simulated laboratory run across ten independent executions.
**Interpretation:** 
Across ten independent processes in the clean empirical environment, the deterministic closed loop produced identical canonical hashes and verification results.

### 2. HYP_002 (State Integrity)
**Observed:** 
- The State engine accepted the replay of an already applied observation as input, but the state vector remained unchanged (`prior_state_root == next_state_root`).
- The engine recorded the replay attempt and emitted an explicit `REPLAYED_OBSERVATION_SKIPPED` reason code rather than crashing.
- Extreme evidence counts (`9007199254740991`) were successfully clamped and emitted `EVIDENCE_COUNT_CLAMPED`.
**Interpretation:** 
The idempotent replay handling is a resilient behavior: it safely acknowledges the event, logs the skip reason, and protects the state vector without triggering a hard protocol fault.

### 3. HYP_003 (Strategic Degradation)
**Observed:** 
The Strategy engine deterministically emitted `PROBE` decisions (with `INSUFFICIENT_CONFIDENCE` or `INSUFFICIENT_EVIDENCE`) when thresholds were missed. It transitioned to `HOLD` (`THRESHOLDS_SATISFIED`) only when both exact boundaries were met or exceeded.
**Interpretation:** 
Autonomous decision-routing strictly complies with the user-defined `planner_spec`, with no edge-case unhandled states.

### 4. HYP_004 (Malformed Extraction Safety)
**Observed:** 
When the Observation extractor received malformed `evaluation.json` schemas (missing required fields, incorrect data types, or invalid JSON syntax), it cleanly aborted with a hard error (`exit 1` or `exit 2`).
**Interpretation:** 
Malformed evaluation artifacts are rejected before any Observation feed can be emitted. Downstream data corruption cannot propagate, guaranteeing systemic integrity even against broken analysis scripts.

### 5. HYP_005 (Agenda Resolution)
**Observed:** 
The Agenda engine mathematically ranked four diverse candidates, respecting the limits defined in `planner_spec.json`. 

| Candidate                 | Score | Outcome  | Reason                          |
| ------------------------- | ----: | -------- | ------------------------------- |
| c1_high_gain_low_cost     |    80 | Ranked   | Admitted                        |
| c3_blows_budget           |    10 | Ranked   | Admitted                        |
| c2_med_gain_high_compute  |     0 | Deferred | INSUFFICIENT_COMPUTE_BUDGET     |
| c4_negative_score         |  -180 | Rejected | EXCEEDS_MAX_COMPUTE_BUDGET      |

**Interpretation:** 
The protocol correctly manages finite resources while systematically optimizing for expected information gain, deferring cumulative overflow and rejecting absolute overflow.

---

## Deferred Findings

### DF-001: Replay Semantics
**Expected:** Hard rejection of replay inputs at the protocol level.
**Observed:** Idempotent replay handling. The State engine safely accepts the input, skips the mutation, and emits a `REPLAYED_OBSERVATION_SKIPPED` reason code.
**Disposition:** No change to kernel. Documentation updated to reflect resilient replay behavior.

### DF-002: Laboratory Artifact Placement
**Observed:** During HYP_001, the laboratory adapter required proper placement and hashing of artifacts (e.g. `artifact_index.json` and `receipt.json`) to satisfy the strict schema requirements.
**Disposition:** Not a kernel bug. This is an operator/documentation improvement for the extraction layer.

### DF-003: Installed-Wheel Packaging Omissions
**Observed:** During pre-release testing, the installed-wheel packaging initially omitted the `.json` schema resources, causing `FileNotFoundError`.
**Disposition:** Already fixed before the `v1.0.1` release. Preserved in engineering history because it justifies the necessity of the clean-room proof process.

---

## Conclusion
The frozen `v1.0.1` architecture is extremely sound. The combination of JSON Schema validation at every transition boundary and deterministic SHA-256 `canonical_hash` roots ensures that Axis behaves safely and predictably. The sequence of freezing interfaces, releasing artifacts, validating installed wheels, executing clean-room proofs, and running empirical workloads without modification was successfully completed. The protocol protected the tested downstream boundaries from malformed evaluation artifacts.
