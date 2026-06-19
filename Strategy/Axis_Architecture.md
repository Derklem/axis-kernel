# Axis Architecture Overview

The Axis Governance System is a self-hosting constitutional enforcement layer. It bridges the gap between raw code changes and a persistent, auditable record of governance decisions. By strictly separating observation, consensus logic, physical mutation, and immutable ledger verification, the Axis ensures mathematical rigor without overriding human authority.

---

## 1. Core Workflow Flowchart

The system operates strictly across the boundary of an advisory pipeline and an immutable ledger.

```text
       [Developer]
            │
            ▼ (git commit)
  ┌───────────────────┐
  │ Pre-Commit Hook   │
  └────────┬──────────┘
           │ (diff / no mutation)
           ▼
  ┌───────────────────┐
  │ Receptor Pipeline │
  │  (Dry-Run Mode)   │
  └────────┬──────────┘
           │ (Risk Score / Semantics)
           ▼
  ┌───────────────────┐
  │ Multi-Auditor     │
  │ Consensus Engine  │
  └────────┬──────────┘
           │ (ANY_QUARANTINE_WINS)
           ▼
  ┌───────────────────┐      Quarantine?      ┌─────────────────────────┐
  │ Immutable Ledger  │ ────────────────────► │ Debt & Recovery Loop    │
  │ (receptor_ledger) │    (Adjudication)     │ (Propose / Verify / Fix)│
  └────────┬──────────┘                       └─────────────────────────┘
           │
           ▼
  ┌───────────────────┐
  │ Replay Engine     │
  │ (21 Invariants)   │
  └───────────────────┘
```

---

## 2. State Semantics: What Mutates and What Doesn't

The architectural ethos of Axis relies on maintaining an **Advisory Boundary**:

### Physical State (Mutates)
- **Codebase / Files**: Modified directly by developers.
- **Recovery Patch Application**: When a human executes `--apply-recovery --force-apply`, the pipeline mutates the filesystem to apply a patch.

### Ledger State (Append-Only)
- **`receptor_ledger.jsonl`**: Every observation, verdict, multi-auditor consensus, and recovery proposal is emitted as a new receipt. The ledger is **append-only**. Nothing is ever deleted. If a mistake is made, a compensating receipt (like `ADJUDICATION_RULING`) is emitted to override it.

### Read-Only (Advisory)
- **Replay Verification (`replay_receptor_chain.py`)**: Computes system health strictly by reading the ledger.
- **Pre-Commit Hook**: Checks the diff without mutating the ledger or the code. Only blocks or accepts.
- **Operator Console (`receptor_console.py`)**: Computes debt maps and system status strictly by reading the ledger.

---

## 3. The Constitutional Invariants

The Replay Engine ensures the cryptographic and logical integrity of the ledger. If the ledger is manually edited, these invariants will fail and the system will halt.

*Note: The numbering reflects the chronological evolution of the system's doctrine; some numerical IDs are merged or implicitly managed as the system matured.*

- **Invariant 1 (Chain continuity):** Receipts must chronologically link, forming an unbroken chain.
- **Invariant 2 (Observation before evidence):** A target must be observed before evidence/scoring is generated.
- **Invariant 3 (Evidence before verdict):** A verdict cannot be rendered until evidence is collected.
- **Invariant 4 (Promoted Evidence Integrity):** An `ACCEPTED` verdict requires valid JSON syntax and an exact hash match between the evidence and the physical file.
- **Invariant 5 (Quarantine Legitimacy):** Quarantines must explicitly state the failed semantic gate or reason.
- **Invariant 6 (No Orphan Verdicts):** Every verdict must trace back to an active case observation.
- **Invariant 7 (Replay Head Consistency):** The final computed chain head must exactly match the head recorded in the physical state file.
- **Invariant 9 (Anti-Sprawl):** Files outside the designated strategy surface cannot falsely claim validator authority.
- **Invariant 10 (Governance Sequence):** Governance evaluation (Distress scoring) must follow an `ACCEPTED` commit.
- **Invariant 11 (Derivable Weight):** Governance weights and versions must perfectly match the deployed physical logic.
- **Invariant 12 (Commit Cumulative Validation):** A commit is only valid if all its child files pass the required ACCEPT/QUARANTINE states.
- **Invariant 13 (Distress Validity):** A distress signal is only valid if the chronologically computed session burden matches the ledger's recorded burden.
- **Invariant 15 (Purely Derivable State):** Telemetry (session burden, commit counts, open quarantines) must be perfectly reproducible from the raw append-only event stream.
- **Invariant 16 (Dry-Run Purity):** Receipts generated during a CI or pre-commit dry-run (`CHECK_ONLY`) must mathematically assert they performed zero state mutation.
- **Invariant 17 (Adjudication Integrity):** Human overrides must reference a valid open quarantine and cannot override fundamental physical constraints (like missing files or corrupted JSON).
- **Invariant 18 (Auditor Receipt Integrity):** Individual auditor verdicts must be tied to a formal review request and cannot bypass physical checks.
- **Invariant 19 (Multi-Auditor Consensus):** Consensus verdicts must accurately reflect the mathematical combination of individual verdicts according to the declared strategy (`ANY_QUARANTINE_WINS`).
- **Invariant 20 (Recovery Proposal Integrity):** A recovery patch proposal must target an explicitly active (non-adjudicated) quarantine case.
- **Invariant 21 (Hash-based Lineage for Recoveries):** Applied recoveries must perfectly match the cryptographically proposed patch hash, completing the debt lifecycle.
