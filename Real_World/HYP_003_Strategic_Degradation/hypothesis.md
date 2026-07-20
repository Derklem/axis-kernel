# HYP_003: Strategic Degradation

## Scientific prediction
Passing edge-case state vectors into the Strategy engine—specifically those at exactly the boundary values defined in the strategy spec, or with low confidence/evidence—will result in deterministic decision routing strictly dictated by the mathematical thresholds in the specification, without logical degradation or schema exceptions.

## Protocol expectations
* The Strategy wheel is installed via pip from the frozen distribution.
* The Strategy engine receives varied state vectors and a strategy spec (strategy-hello-v1).
* State vectors with confidence < probe_threshold produce a PROBE decision (Reason: INSUFFICIENT_CONFIDENCE).
* State vectors with confidence >= probe_threshold but evidence_count < minimum_evidence produce a PROBE decision (Reason: INSUFFICIENT_EVIDENCE).
* State vectors meeting both thresholds exactly (or exceeding them) produce a HOLD decision (Reason: THRESHOLDS_SATISFIED).

## Observed result
**Prediction confirmed.** 
The sealed kernel perfectly executed all decision logic across boundary values without degradation or schema breakdown.
1. When confidence (49) was just below the threshold (50), the engine deterministically emitted PROBE (INSUFFICIENT_CONFIDENCE).
2. When confidence matched exactly (50) but evidence (99) was just below minimum (100), it emitted PROBE (INSUFFICIENT_EVIDENCE).
3. When both parameters identically matched the thresholds, it successfully flipped to HOLD (THRESHOLDS_SATISFIED).
4. When both parameters vastly exceeded the thresholds (99 and 5000), it safely maintained HOLD without overflow.

The strategy-hello-v1 evaluation loop is logically sound.
