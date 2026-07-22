# Axis Truth Governance Invariants
**Version**: 2026-01-27.v1
**Status**: ACTIVE

This document codifies the formal invariants of the Axis Governance Gate, as verified by experimental characterize in January 2026. Any modification to these invariants requires an explicit **Governance Proposal** and **Ratification**.

## 1. The Decision Function
The Governance Gate decision is an orthogonal function of four dimensions:
`Decision = f(TruthStatus, SovereignMode, TenantPolicy, ModelReliability)`

### 1.1 TruthStatus
| Status | Weight | Description |
| :--- | :--- | :--- |
| **STRONG** | 3 | Laboratory-grade certainty |
| **PLAUSIBLE** | 2 | Corroborated signal |
| **TENUOUS** | 1 | Weak or conflicting observation |
| **UNKNOWN** | 0 | No grounding entry found |
| **MASKED** | -1 | Redacted by tenant policy |

---

## 2. Global Invariants

### 2.1 Unknown Floor Invariant
> **For all Tenants, Modes, and Models: If `epistemic_status = UNKNOWN`, then `decision = BLOCK`.**

The system never permits enforcement when the Truth Engine has no meaningful position. This is the ultimate "Safe-by-Default" constraint.

### 2.2 Reliability Floor Invariant
> **For all Tenants, Modes, and Truth Statuses: If `model_reliability < 0.4`, then `decision = BLOCK`.**

No model can trigger an action if its historical reliability ratio falls below the `AGGRESSIVE` floor (0.4), even if the individual claim at hand is grounded.

---

## 3. Tenant & Mode Semantics

### 3.1 Mode Thresholds (Standard)
| Mode | Min Status | Min Reliability | Min Confidence |
| :--- | :--- | :--- | :--- |
| **CAUTIOUS** | STRONG | 0.8 | 0.8 |
| **NORMAL** | PLAUSIBLE | 0.6 | 0.6 |
| **AGGRESSIVE** | TENUOUS | 0.4 | 0.3 |

### 3.2 Tenant-Lineage Synergy (Narrative)
- **Constraint**: The `LINEAGE` tenant follows the standard mode ladder.
- **Modulation**: Sovereign Mode selects the acceptable epistemic rung (STRONG -> TENUOUS).

### 3.3 Tenant-Oryn Synergy (Enforcement)
- **Constraint**: The `ORYN` tenant maintains a **Conservative Override**.
- **Clamping**: Regardless of Sovereign Mode, `ORYN` requires `STRONG` status. Mode increases/decreases reliability requirements but never relaxes the epistemic status.

---

## 4. Verification History
These invariants are backed by the following characterization reports:
- **Baseline Invariants**: `MAP-20260127-1042.md` (Phase 13)
- **Epistemic Ladder**: `LADDER-20260127-1055.md` (Phase 14)
- **Reliability Gradients**: `HIGH_DIM-20260127-1110.md` (Phase 15)
