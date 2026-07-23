# Axis Kernel Release Process

This document defines the authoritative release process for the Axis Kernel. It describes the lifecycle of a release from feature completion to public availability. This is not a mechanical checklist, but a disciplined engineering process designed to ensure that every release is verifiable, deterministic, and safe.

## 1. Feature Complete
The core logic for the release must be implemented, reviewed, and merged into the working branch. All architectural decisions must be documented.

## 2. Tests Pass
The automated test suite must execute successfully. This includes:
- Component-level unit tests (e.g., \Planner/tests/\, \ProposalGateway/tests/\)
- The repository boot smoke test (\	ests/smoke/test_repository_boot.py\)

## 3. Replay Deterministic
The execution must be verifiable. Any stochastic systems (like the Planner) must have their outputs routed through the deterministic Proposal Gateway, producing artifacts that can be audited and replayed. 

## 4. Canary Complete
Before a full release, new capabilities must be proven in Shadow Mode, and then safely validated in Canary Mode. We require empirical evidence that the agent operates safely within the boundaries of the Governance Kernel before proceeding.

## 5. Repository Audit
The Git repository must be audited to prevent bloat and maintain a clean public history:
- Ensure no oversized generated artifacts (e.g., large \.zip\ files, multi-gigabyte telemetry logs) have been accidentally committed.
- Verify \.gitignore\ accurately reflects the current architecture's runtime state and cache directories.

## 6. Fresh-Clone Verification
The release candidate must be pushed to a remote branch and verified from a completely fresh clone:
- Clone the repository into a new, isolated directory.
- Verify the repository footprint size.
- Ensure the smoke tests pass without relying on pre-existing development environment state.

## 7. Release Notes
Draft factual, observable release notes. The notes must accurately describe:
- What has changed (e.g., architectural integrations, new execution modes).
- Upgrade notes for external contributors (e.g., changes to configuration or environment assumptions).

## 8. Tag
Once verified, the repository must be tagged with the official version number (e.g., \xis-kernel-v1.0.3\) to establish an immutable baseline for the release.

## 9. GitHub Verification
Push the tag and the commits to GitHub. Verify the remote SHAs match the local repository perfectly, ensuring the public state accurately reflects the intended release candidate.

## 10. Public Announcement
Publish the announcement thread. The narrative should lead with the engineering work, empirical findings, and architectural advancements that justify the release.
