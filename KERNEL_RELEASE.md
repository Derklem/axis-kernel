# Axis Kernel Release
**Release ID**: axis-kernel-v1.0.1
**Commit Hash**: c2c9bcacd1137496826313bbf91dc388cc8884e4
**Proof Result**: PASS

## Introduction
This release represents the frozen, verified core of the Axis protocol (Phase 2), encompassing Strategy, Laboratory, Observation, and State engines. The deterministic proof loop has been executed in a clean environment, verifying that all state transitions and validation constraints form a reproducible, closed loop.

## Package Versions and Hashes
| Package | Version | Distribution Hash (SHA-256) |
| --- | --- | --- |
| `laboratory` | 0.2.1 | `7343380953ce492841ab17f1de37273dbd09624891932f842a8cf273dabfb17b` |
| `observation` | 0.2.0 | `6c582427af848baff20df022ece3145c95b61453db512eb7becf4395f85a5750` |
| `state` | 0.2.0 | `37001baa0bc560df4af30d399e763bd7c9736bad82b0e1b06023db438074eb00` |
| `strategy` | 0.3.0 | `a784303aad5ce8db668f3c438ec265b6ac1bd826bedeeecdfce283e0e6cc5f09` |

**Rust Verifier Binary Hash (SHA-256):**
`0ee9d371a05cc9a0c223a3266cff7d872a9e7d5b2b3a85905edf0dce7a33708b`

## Protocol Dependencies
*(Note: Protocol document hashes in `kernel_release.json` are computed as raw UTF-8 bytes over the markdown file contents.)*
- Laboratory ensures execution reproducibility and canonical payload evaluation.
- Observation extracts state delta feeds tightly coupled to dual-verifier evidence (`verification.json`).
- State manages transitions immutably given the Observation feed.
- Strategy closes the loop by projecting deterministic policies (PROBE/HOLD) against the current State Vector.

## Release Proof Execution
Run `scripts/release_proof.ps1` to re-execute the clean-room compilation, packaging, and validation test suite (`Strategy/scripts/prove_loop.py`).

## Deferred Work (NOT part of kernel)
To prevent accidental scope creep, the following components are explicitly excluded from the frozen kernel boundaries:
- Common protocol envelope
- Distributed execution
- Estimation engine
- Adaptive scoring
- Learning
- Governance
