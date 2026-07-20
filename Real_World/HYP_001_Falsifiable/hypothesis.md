# HYP_001: Installed-Wheel Canonical-Hash Reproducibility

## Scientific prediction
Running the canonical hashing function provided by the installed frozen Laboratory wheel against a fixed, non-trivial JSON payload will produce identical 64-character roots across ten entirely independent processes.

## Protocol expectations
* The Laboratory wheel is installed via pip from the frozen distribution.
* Observation extraction yields a valid feed matching the 1.0.0 schema for each run.
* State incrementally consumes the feeds.
* Strategy receives the sequence of feeds and eventually emits a decision.

## Observed result
**Prediction confirmed.** All 10 independent subprocesses produced the exact same 64-character root 2752a7751627d91abbf2c0d41eff223f31e2448b9a0e52ae96348b7d51ca0b0b.

**Protocol expectations confirmed.** 
1. The pipeline successfully propagated data from Laboratory -> Observation -> State -> Strategy.
2. The erify-strict tool passed on all runs using the Rust verifier.
3. We observed the protocol working as intended: the un adapter had to correctly output artifacts to LAB_ARTIFACTS_DIR to be included in the receipt. The strict type validation prevented a float from being canonically hashed.
4. The Strategy loop emitted a final decision of PROBE (Reason: INSUFFICIENT_CONFIDENCE) as expected.

All schemas and invariants held up under the sealed v1.0.1 kernel. No modifications to the kernel were required to complete the experiment.
