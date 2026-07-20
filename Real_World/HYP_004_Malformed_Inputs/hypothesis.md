# HYP_004: Malformed Extraction Safety

## Scientific prediction
Passing corrupted or malformed evaluation artifacts (e.g., missing required fields, type mismatches, or completely invalid JSON) into the Observation extractor will gracefully abort, yielding a hard error rather than silently processing invalid evidence or crashing downstream components.

## Protocol expectations
* The Observation wheel is installed via pip from the frozen distribution.
* The Observation engine receives various malformed evaluation.json files alongside a valid manifest.
* Missing required fields (e.g., observed) yield a schema validation failure.
* Incorrect types (e.g., string instead of integer) yield a schema validation failure.
* Invalid raw JSON syntax yields a JSON decoding failure.
* Downstream components (State) are completely protected from receiving malformed payload structures because the pipeline aborts at the extraction layer.

## Observed result
**Prediction confirmed.** 
The Observation CLI strictly validates the evaluation.json artifact against the frozen evaluation.json JSON schema.
1. When passed a JSON missing fields, it safely aborted with exit code 1 (schema validation error).
2. When passed incorrect types, it safely aborted with exit code 1.
3. When passed invalid JSON syntax, it cleanly aborted with exit code 1 (JSONDecodeError).

This behavior acts as a strict firewall. The State vector cannot be corrupted by malformed scientific artifacts because the Observation layer refuses to serialize them into a eed. Systemic safety is fully maintained under the sealed v1.0.1 kernel.
