# Security & Assumptions

This document outlines the operational and cryptographic assumptions underpinning the Laboratory v0.1.0 protocol.

## Cryptographic Assumptions

1. **SHA-256 Collision Resistance**: We assume it is computationally infeasible for an adversary to generate two different JSON payloads or files that result in the same SHA-256 hash. If SHA-256 is broken, the protocol's guarantees are voided.
2. **Canonical Serialization Stability**: We assume the Python `json` module's deterministic sorting (`sort_keys=True`) is stable across the supported Python versions. Any deviation in how unicode or floats are serialized would cause false-positive verification failures.

## Locking & Concurrency Assumptions

The ledger append mechanism relies on a filesystem-level atomic operation (`os.mkdir` / `Path.mkdir`) to create a spin-lock directory (`.ledger.lock`). 
- We assume the host filesystem (e.g., NTFS, ext4, APFS) strictly adheres to POSIX atomic directory creation semantics. 
- If the filesystem is a network mount (e.g., NFS, SMB) that poorly implements atomic directory locks, concurrent writes could theoretically race and corrupt the ledger sequence.

## Trust Boundaries

- **The Runner (`runner.py`)**: Is considered an untrusted boundary. It executes arbitrary subprocesses. It is expected that the subprocess might behave erratically. The runner's only job is to blindly capture the exact outputs and exit codes without attempting to parse or trust them.
- **The Verifier (`verifier.py`)**: Is considered the ultimate source of truth. It operates strictly as a read-only process and holds the authority to declare evidence `PASS`, `FAIL`, or `UNVERIFIABLE`.

## Known Limitations

- **Large Ledger Memory Footprint**: Currently, `lab verify` loads the entire ledger sequence into memory to validate the chain. For ledgers containing millions of events, this could result in OOM (Out of Memory) constraints. Future protocol versions may allow windowed verification or checkpoints.
- **Orphaned Runs on SIGKILL**: If the `lab run` process is abruptly killed via `SIGKILL` (where Python cannot execute `finally` blocks), a `RUN_STARTED` event will be orphaned in the ledger without a terminal event. This is safely handled by the verifier (`UNVERIFIABLE`), but will leave dead events in the chain.
