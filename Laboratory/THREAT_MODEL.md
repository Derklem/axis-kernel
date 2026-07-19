# Threat Model

The Laboratory protocol provides specific cryptographic guarantees about evidence integrity. To trust these guarantees, it is critical to understand exactly what the protocol protects against, and what relies on out-of-band security.

## In-Scope Protections

The Laboratory is designed to detect and reject the following attacks:

1. **Post-run Modification**: Any alteration of inputs, outputs (`stdout.txt`, `stderr.txt`), or artifacts after the run has been completed.
2. **Receipt Tampering**: Modifying the evaluation results, timestamps, or declared hashes within `receipt.json`.
3. **Ledger Corruption**: Modifying payloads, breaking the hash chain, duplicating events, or reordering the `ledger.jsonl` file.
4. **Undeclared Evidence**: Adding rogue files to the `inputs/` or `artifacts/` directories after the run has completed. The verifier enforces an *exact* manifest match.
5. **Replay & Identity Ambiguity (The Evil Twin)**: Copying a valid run directory and mutating the `run_id` to claim ownership of another run's artifacts. 
6. **Cross-contamination**: Swapping `receipt.json` files between two different, valid runs.

## Out-of-Scope (Unprotected)

The Laboratory assumes a secure execution environment up to the point of freezing. It **does not** protect against:

1. **Malicious Code Before Freezing**: If the executing script alters its own inputs *during* execution before the receipt is generated, the Laboratory will blindly hash the altered state.
2. **Kernel or OS Compromise**: A compromised host OS that lies to the Python interpreter about filesystem contents or intercepts filesystem syscalls.
3. **Python Interpreter Compromise**: Malicious alteration of the `hashlib` or `json` libraries executing the verification.
4. **Hardware Faults**: Bit flips occurring in RAM before the payload is serialized and flushed to disk.
5. **Ledger Deletion**: An adversary deleting the entire `ledger.jsonl` file. The protocol can prove tampering of existing records, but it cannot prevent the physical destruction of the chain itself (though a missing ledger will rightfully yield `UNVERIFIABLE`).
