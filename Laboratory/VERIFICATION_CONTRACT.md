# Verification Contract

The Laboratory protocol defines a strict, normative verification registry. For an independent implementation to claim protocol conformance, a verifier MUST execute checks in registry order and emit the exact ordered prefix ending at the first mandatory halt. A non-halted verification emits all 17 checks.

## Status Escalation

All checks evaluate to one of three statuses:
- `PASS`: The check succeeded.
- `FAIL`: The check failed because the evidence is corrupt or invalid.
- `UNVERIFIABLE`: The check failed because required evidence is missing or unreadable.

The overall status of a verification run is determined by monotonically escalating the most severe failure encountered:
`FAIL > UNVERIFIABLE > PASS`. 

A subsequent `UNVERIFIABLE` check cannot downgrade an existing `FAIL` overall status.

## Normative Check Registry

A compliant verifier MUST emit exactly the following checks in order:

### Ledger Verification
1. `ledger_load`: Can the ledger be located and parsed as JSONL? (Halt on failure)
2. `ledger_chain`: Are sequences monotonic, previous hashes correct, and recomputed canonical hashes exact? (Halt on failure)

### Event Presence
3. `run_started_event`: Does exactly ONE `RUN_STARTED` event exist for this `run_id`? (Halt on failure)
4. `terminal_event`: Does exactly ONE terminal event (`RUN_COMPLETED`, `RUN_FAILED`, `RUN_ABORTED`) exist for this `run_id`? (Halt on failure)
5. `terminal_event_sequence`: Does the terminal event occur strictly after the `RUN_STARTED` event?

### Receipt Verification
6. `receipt_presence`: Does `receipt.json` exist? (Halt on failure)
7. `receipt_schema`: Does the receipt pass JSON Schema validation against `receipt.json` (Draft 7)? (Halt on failure)
8. `receipt_hash`: Does the recomputed canonical hash of `receipt.json` exactly match `receipt_hash` in the terminal event?
9. `run_started_link`: Does `receipt.run_started_hash` exactly match the hash of the `RUN_STARTED` event?

### Experiment Verification
10. `experiment_presence`: Does `experiment.json` exist? (Halt on failure)
11. `experiment_schema`: Does it pass schema validation? (Halt on failure)
12. `experiment_hash`: Does the recomputed canonical hash of `experiment.json` exactly match `receipt.experiment_hash`?
13. `start_experiment_hash`: Does `receipt.experiment_hash` match the `experiment_hash` recorded in the `RUN_STARTED` payload?

### File Manifests
14. `inputs_manifest`: Do all declared input hashes match files exactly, with no undeclared files in `inputs/`?
15. `artifacts_manifest`: Do all declared artifact hashes match files exactly, with no undeclared files in `artifacts/`?
16. `stdout_hash`: Does the hash of `stdout.txt` exactly match `receipt.execution.stdout_hash`?
17. `stderr_hash`: Does the hash of `stderr.txt` exactly match `receipt.execution.stderr_hash`?
