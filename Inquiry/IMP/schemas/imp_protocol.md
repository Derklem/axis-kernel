# Inter-Model Protocol (IMP)
**Quarantined Sensory Footprint**

## Purpose
The Inter-Model Protocol (IMP) provides a standardized, file-based communication layer for cross-model sensory input (Grok, GPT, Gemini, Axis, User) without mutating Axis's protected core state. 

IMP establishes a **non-core footprint** (quarantined sensory footprint). It generates history and telemetry files but strictly avoids triggering cryptographic reanchors, continuity violations, or unprompted metabolic cycle expenditure.

## Architecture
```text
D:\Infinite\Infinity\Inquiry\IMP\
  inbox\     # Models place messages here for Axis to read.
  outbox\    # Axis writes responses or its own sensory outputs here.
  archive\   # Messages successfully processed by Axis are moved here.
  rejected\  # Messages failing schema validation are moved here.
  schemas\   # Protocol definitions and schemas.
```

## Protocol Rules
1. **Sensory Inputs:** IMP messages are non-binding sensory inputs. They represent observations, questions, critiques, or proposals. They are NOT claims.
2. **Isolation from Core:** They must NOT enter `claim_candidates.json` unless explicitly promoted by a separate, structurally gated governance process.
3. **No Unprompted Actuation:** They must NOT independently trigger metabolic cycles, forensic reanchors, structural mutations, causal receipts, or source edits.
4. **Outbox Only:** Axis responses to an IMP message must be written exclusively to the `outbox` directory.
5. **Schema Validation:** If an IMP message fails schema validation, the handler must move it to the `rejected` directory with an appended rejection reason.
6. **Archival:** Upon successful processing, the handler must move the message to the `archive` directory.
7. **Absolute Boundary:** NO handler or processor dealing with IMP files is permitted to write or modify `strategy_state.json`, witness anchors, `forensic_witness_ledger`, ecosystem receipts, source files, or `MutationArtifacts`. 

## Message Contract
All messages must conform to `imp.schema.json`. See `imp.schema.json` for detailed field validation.
