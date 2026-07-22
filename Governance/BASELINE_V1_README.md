# AXIS_GOVERNANCE_BASELINE_V1

## Overview

This baseline freezes the Axis governance and peripheral architecture. It serves as a known-stable named release establishing an explicit boundary between conversational inputs and the epistemic metabolism. This named release can be returned to should future operational experiments or tooling integrations degrade the integrity of the system.

## Baseline Guarantees

This architecture enforces the following structural guarantees:

1. **Explicit Lane Classification:**
   All external inputs bridged to the system are explicitly classified and routed by `lane_router.py`. Unknown or unclassified noise is rejected outright rather than defaulting to ambiguous states.

2. **Witnessed Admission Gate:**
   Any input flagged as possessing epistemic weight (`witnessed`) is sequestered in a staging queue. Entering the true metabolic layer (`Direct_Inquiry.jsonl`) requires an explicit operator acknowledgment (`operator_ack`, `epistemic_cost_ack`) validated via `witness_admission.py`.

3. **Read-Only Conversational Surface:**
   The conversational layer (`axis_conversation_surface.py`) is locked into a synthesis-only telemetry mode. It narrates system state and provides a conversational "voice" but is structurally isolated from executing any candidate mutations or ledger updates.

4. **Governance Audit Mode:**
   A continuous auditing layer (`governance_audit.py`) guarantees routing compliance, separating historical bypass counts from active structural breaches.

5. **Autonomy Policy V1:**
   System autonomy is no longer a monolith. The explicit autonomy policy strictly allows observation and surface narration while explicitly forbidding autonomous epistemic processing, admissions, or self-modification.

6. **No StrategyEngine Changes:**
   This baseline introduces no core ledger mutations, requires no daemon restarts, invokes no StrategyEngine processing, and enacts no temporal reanchoring. It strictly orchestrates the pre-metabolic governance perimeter.
