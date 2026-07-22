# Strategy Protocol

This document defines the normative rule for the `strategy-hello-v1` decision experiment.

## Input

- **State Vector**
- **Strategy Specification**
- **Observation Feed**

## Output

- **Decision Artifact**

## Evaluation Order

1. Validate schemas for all inputs.
2. Construct input envelope.
3. Canonical hash envelope to produce `input_root`.
4. Evaluate confidence threshold:
   - If `state.confidence < strategy_spec.probe_threshold`, emit `PROBE` with `INSUFFICIENT_CONFIDENCE`.
5. Evaluate evidence threshold:
   - If `state.evidence_count < strategy_spec.minimum_evidence`, emit `PROBE` with `INSUFFICIENT_EVIDENCE`.
6. Else, emit `HOLD` with `THRESHOLDS_SATISFIED`.
7. Emit immutable decision artifact containing `input_root`.
