# Axis Kernel v1.0.1

This release freezes the first publicly documented Axis deterministic protocol kernel for reproducible experimental workflows.

## Included components

* Laboratory
* Observation
* State
* Strategy

## Release verification

* Clean-room installed-wheel proof: PASS
* Python/Rust verification path: PASS
* Source stress suite: PASS
* Installed-wheel stress suite: PASS
* Release commit: `aa0586d5505b49b28abb41af9528090942e9c631`
* Rust verifier SHA-256: `0ee9d371a05cc9a0c223a3266cff7d872a9e7d5b2b3a85905edf0dce7a33708b`

## Empirical study

Five empirical scenarios exercised canonical-hash reproducibility, replay safety, strategy boundaries, malformed-input rejection, and resource-constrained Agenda behavior without modifying the frozen kernel.

See `Real_World/notes.md` for observed results, interpretations, and deferred findings.

## Version discipline

The semantics of `axis-kernel-v1.0.1` are frozen. Any future behavioral correction will receive a new version identifier.
