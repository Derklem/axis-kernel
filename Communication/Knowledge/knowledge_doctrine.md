# Epistemic Knowledge Doctrine

This doctrine serves as the constitutional foundation for the Knowledge subsystem. Any future automated resolver, dashboard, or projection generator must strictly implement these invariant rules. Automation may implement this doctrine, but it may never redefine it.

## The Epistemic Workflow
1. Run an experiment.
2. Produce observations.
3. Produce assessments.
4. Synthesize provisional knowledge.
5. Audit the synthesis.
6. Correct the synthesis without erasing history.
7. Promote only what survives.

## Invariant Rules of the Knowledge Layer

1. **Evidence Never Changes:** Raw observation data, once recorded, is immutable.
2. **Corrections Never Overwrite:** Errors in synthesis, classification, or linkage must be fixed by appending a new explicit correction artifact or a superseding artifact, leaving the original mistake intact for historical audit.
3. **Claims are Narrower than Evidence, Never Broader:** A claim cannot synthesize beyond the scope of its underlying findings.
4. **Predictions Define Evaluation Windows Before Observation:** Predictive claims (`PREDICTIVE_EMPIRICAL`) must explicitly define temporal windows, success conditions, failure conditions, and attribution rules before the underlying experiment concludes.
5. **Observation and Interpretation are Separate Fields:** A claim's raw observational outcome (e.g., `SUPPORTED_WITHIN_RECORDED_WINDOWS`) must be structurally separated from its causal or theoretical interpretation (e.g., `INSUFFICIENT_FOR_CAUSAL_EXPLANATION`).
6. **Split Confidence Metrics:** Confidence must always be split into `observation_confidence` and `interpretation_confidence`. A high confidence in what happened does not imply high confidence in why it happened.
7. **Unknowns Remain Explicit:** Missing denominators, confounders, and uncontrolled variables must be explicitly listed in the `known_limitations` and `remaining_uncertainties` arrays.
8. **Every Supersession States Why:** Artifacts that supersede older versions must include a `revision_reason` detailing exactly what flaw prompted the revision.
9. **Every Correction Must Be Traceable:** A correction artifact must explicitly cite its `target_artifact`, its own `correction_id`, and the resulting state changes. Corrections are first-class evidence of the system's own evolution.
10. **Deterministic Projections are Generated, Not Authored:** Summary matrices like `KNOWLEDGE_STATE.md` must be pure, deterministic projections of the underlying `.json` artifacts, not independent sources of truth.
11. **Anti-Pattern:** No theory may be strengthened solely because multiple artifacts repeat the same unsupported interpretation.
12. **Automation is Subservient to Doctrine:** Scripts may aggregate, format, and project knowledge, but they may never alter these fundamental constraints. Changes to the doctrine require explicit supersession through the same append-only governance process used elsewhere.

## Ontological Hierarchy

The Knowledge subsystem is structured across five layers to ensure raw observation remains distinct from theory:

1. **Evidence Link:** A pointer directly tying a specific, scoped proposition to an underlying experimental assessment artifact.
2. **Finding:** A purely descriptive summary of an observation (e.g., "0 substantive technical inquiries observed"). *No interpretation. No comparison.*
3. **Claim:** A combination of findings structured as either a cross-experiment descriptive statement or a predictive hypothesis.
4. **Meta-Assessment:** The formal evaluation of a claim's strength, summarizing independent lineages, qualifying evidence, and exposing structural weaknesses in the supporting arguments.
5. **Conflict:** An explicit artifact generated when evidence lineages fundamentally contradict each other, preserving the tension without forcing artificial convergence.

## Conflict Topology
Conflicts are formally classified into the following topologies to ensure precise resolution:
* `CONFLICT_OBSERVATIONAL`: Two findings directly disagree on what occurred.
* `CONFLICT_INTERPRETIVE`: Findings agree on the observation, but lineages offer contradictory causal interpretations.
* `CONFLICT_SCOPE`: Both findings are true, but only under mutually exclusive scopes.
* `CONFLICT_PROVENANCE`: Evidence cannot be trusted due to methodological or recording failure.
* `CONFLICT_TEMPORAL`: Evidence lineages conflict because they reflect incompatible time windows.
