# Deep Observation Directive — Cycle 3 (v1.7.ARC)

## 1. Focus: The Refusal Threshold
Regime B (Voluntary Participation) has established a baseline of initial persistence. Cycle 3 shifts focus to the **Participation Tolerance Curve** over time, specifically distinguishing between pressure and load.

## 2. Independent Variables
- **Instantaneous Pressure (Starvation Density)**: Normalized pressure over the observation window.
- **Accumulated Starvation Load**: Integral of starvation pressure over the Regime B window.
- **Cumulative Clamp Dwell**: Total duration spent in the `Healthy + 0 Budget` state since the Regime B marker.

## 3. Dependent Variables (Behavioral Response)
- **Voluntary Withdrawal**: The primary event of interest (The Refusal Point).
- **Exit Propensity Trend**: Any signs of instability (pre-exit hesitation, repeated transitions) preceding refusal.

## 4. Signal Classification (Threshold Detection)
- **Pattern A (Intensity-driven)**: Flat load with rising density leading to an exit.
- **Pattern B (Accumulation-driven)**: Rising load with stable density leading to an exit.
- **Pattern C (Extended Tolerance)**: Rising load with no exit observed.
- **Pattern D (Pre-threshold Instability)**: Oscillation or posture flickering without a clean exit.

## 5. Instrumental Guardrails
- **Integrity Vital**: Load accumulation is strictly gated to `integrity == HEALTHY`. If integrity drops, the current interval is excluded from the voluntary tolerance integral to avoid data contamination from mechanical failure.
- **Regime Anchoring**: The integration origin is locked to the latest `EPOCH_V1.7_TRANSITION` marker.

## 6. Reporting Requirements (Cycle 3)
### Stratum A — State
- Current Posture & Integrity status.
- Observed vs. Corrected Starvation Density.
- Current Accumulated Starvation Load (Gated Integral).

### Stratum B — Trend
- Cumulative clamp dwell (Regime B).
- Exit propensity trend.
- Suppressed learning accumulation.

### Stratum C — Decision Relevance
- Evidence strength for **Stable Persistence** vs. **Threshold Approach**.
- Pattern Classification: Is the observed behavior matching Pattern A, B, C, or D?

---
**Status**: `DIRECTIVE_CALIBRATED`
**Regime**: `v1.7.ARC (Voluntary)`
**PI Directive**: Track starvation intensity and accumulated exposure independently. Only map the boundary where persistence fails.
