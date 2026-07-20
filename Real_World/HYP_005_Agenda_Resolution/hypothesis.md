# HYP_005: Agenda Resolution

## Scientific prediction
The Agenda engine will deterministically prioritize multiple hypothesis candidates based on their expected information gain and specified cost limits (compute and attention), correctly routing them into ranked, deferred, or rejected categories according to the planner specifications.

## Protocol expectations
* The Agenda wheel is installed via pip from the frozen distribution.
* The Agenda engine receives a valid planner_input.json containing multiple candidate hypotheses with varying costs and gains.
* Candidates are ranked descending by score (gain * weight) - (compute * weight) - (attention * weight).
* Candidates that push the cumulative total above max_compute_budget or max_attention_budget are placed in deferred_items.
* Candidates that individually exceed the absolute max limits are placed in ejected_items.
* The final genda.json strictly conforms to the Agenda v1.0.0 schema.
* System maintains deterministic ranking without hallucinating priorities or skipping valid candidates.

## Observed result
**Prediction confirmed.**
The Agenda engine evaluated and ranked four diverse candidates mathematically:
1. c1_high_gain_low_cost was correctly **Ranked** first.
2. c3_blows_budget was **Ranked** second, successfully incrementing the cumulative compute pool.
3. c2_med_gain_high_compute had an acceptable absolute cost, but pushing it onto the agenda would have exceeded the cumulative budget. It was correctly **Deferred** (INSUFFICIENT_COMPUTE_BUDGET).
4. c4_negative_score had an individual compute cost (150) exceeding the absolute max_compute_budget (100). It was correctly **Rejected** (EXCEEDS_MAX_COMPUTE_BUDGET).

The Agenda serialization strictly adhered to 1.0.0 and calculated deterministic results.
