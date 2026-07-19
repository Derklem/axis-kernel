# Strategy Engine Extraction

With the completion of **Laboratory v0.2.0**, the protocol guarantees deterministic execution and cryptographic evidence validation across independent implementations. The Laboratory is sealed.

The next Axis component to extract is the **Strategy Engine**, shifting focus from *Execution & Evidence* to *Belief & Decision*.

## Goal
Extract the Strategy Engine into its own independent protocol boundary, complete with a Hello World decision experiment that leverages the Laboratory for its empirical feedback loop.

## Boundary Inventory

The Strategy Engine introduces new primitives that sit on top of the Laboratory:

1. **State Vector**: The current representation of the Engine's beliefs, models, and policy configurations.
2. **Strategy Specification**: A declarative definition of an optimization goal, hypotheses, and decision criteria.
3. **Observation Feed**: Time-series inputs representing telemetry, user feedback, or empirical results.
4. **Decision Artifacts**: The output of a Strategy evaluation, indicating changes to the State Vector or the generation of new Laboratory experiments.
5. **Determinism Audit**: A verifiable check ensuring that the decision engine produces identical decisions given identical State Vectors and Observation Feeds.

## Implementation Plan: "Hello World" Decision Experiment

1. **Initialize the Strategy Subsystem**:
   - Create a new directory structure `Strategy/` alongside `Laboratory/` and `Governance/`.
   - Define a simple State Vector (e.g., a simple parameter tuning model).
2. **Implement the "Hello World" Decision**:
   - Write a Strategy Specification to optimize a single parameter.
   - Use a mock Observation Feed to provide input.
   - Execute the Strategy to produce a Decision Artifact.
3. **Integrate with Laboratory (Mock)**:
   - Generate a mock Laboratory experiment spec based on the decision.
4. **Determinism Audit**:
   - Write a deterministic evaluator that hashes the inputs (State + Spec + Observations) and binds the Decision Artifact to this cryptographic root, proving the decision was reproducible.
