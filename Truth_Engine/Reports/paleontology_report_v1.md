# Paleontology of the Semantic Subsystem

## Subsystem Excavation Table

| Artifact / System | Evidence Type | Finding | Classification |
| :--- | :--- | :--- | :--- |
| `T04_AggregateClaims.ps1` | Code | Produces CLM records | Observed |
| `Service_Registry.json` | Registry | No T04/T05 entries | Observed |
| `Archive_LostPhases.txt` | Archive | Contains mock JSON schemas with `CLM-` references. | **Design Examples** |
| `TE_Claims_Index.jsonl` | Ledger | Fixture/test claims only | Observed |

## Phase 1 Findings: The Lost Phases Archive

**Target:** `D:\Infinite\Foreign\Archive_LostPhases.txt`

**Extraction:**
A search for `CLM-` within this archive yielded four structural matches within JSON blocks.

**Context Examples:**
```json
{
  "claim_id": "CLM-20260126-0001",
  "normalized_text": "There will be a record-breaking snowstorm in Texas every 10 years in years ending in 6."
}
```
```json
{
  "evidence_refs": ["CLM-...", "CNT-..."],
}
```
```json
{
  "linked_claims": ["CLM-bots-001"]
}
```

**Analysis:**
This file is a raw chat history dump containing the original design dialogue from January 26, 2026 (the exact date the Truth Engine prototypes were created). The `CLM-` references found here are not historical operational records. They are **design examples** and hypothetical schemas used to blueprint the Truth Engine. This confirms that the semantic layer was heavily architected and planned, but it does not provide evidence that it ever generated organic claims in production.

## Phase 2 Findings: Historical Ledgers and Legacy Consumers

**Target:** `D:\Infinite\Infinity\Archive\`, `\Backups\`, and `\Truth_Engine\Content\`
**Extraction:** A recursive search for older/archived ledgers (`.bak`, `.old`, `.jsonl`, `.json`) that might contain older, overwritten versions of `TE_Claims_Index`.
**Finding:** **Zero archived ledgers exist.** If the Semantic Subsystem had ever operated at scale and been overwritten or deprecated, there would be `.bak` files (the system creates these prolifically for other components like `Doctrine_Rules` and `Tool_Registry`). The absence of any historical claim ledger strongly implies the single frozen ledger from Jan 27 is the *only* one that has ever existed.

**Target:** Global search for `CLM-` outside the Truth Engine folder.
**Extraction:** Found references inside:
- `Verification_Behavioral_Hooks.ps1`
- `Verification_Research_Loops.ps1`
- `Verification_Tenant_Views.ps1`
- `Verification_Truth_Conditioning.ps1`

**Analysis:**
These files are **Test Harnesses**. For example, `Verification_Truth_Conditioning.ps1` explicitly hardcodes the `CLM-T` fixture to test the Oryn Shield:
> `# Claim CLM-T (Weak Signal) is TENUOUS. LOCK_DEVICE requires STRONG.`
> `$lockDecision = & $orynShield -ActionType "LOCK_DEVICE" -Justification "Suspicious weak signal detected."`

This proves that `CLM-` identifiers outside the ledger were explicitly built to act as mock data for unit tests validating the immune system.

## Phase 3 Findings: Research Layer Activation
We found `CLM-T` inside the `TE_Observations_Log.jsonl`, `TE_Research_Targets.jsonl`, and `TE_Research_Probes.jsonl`.
Extracting those lines revealed:
```json
{"timestamp":"2026-01-27T16:54:10.8061109Z","claim_id":"CLM-T","canonical_text":"Weak Signal","current_status":"TENUOUS","usage_count":6,"selection_reason":"Overused TENUOUS claim (6 usages)","priority":1}
{"timestamp":"2026-01-27T16:54:10.9707089Z","source":"TRUTH-RESEARCH-001","content":"RESEARCH_CORROBORATION: No new contradictory evidence found during scan. (Target: CLM-T)"}
```
This demonstrates the Truth Engine's Research service (`TRUTH-RESEARCH-001`) activated on Jan 27 to investigate the `CLM-T` test fixture. The system ran a full cycle against its own mock data.

---

## Conclusion: Final Verdict

> [!IMPORTANT]
> The leading explanation for the Semantic Subsystem (T04/T05) is **Hypothesis C: A Test Harness / Prototype**.
>
> 1. **No Evidence of Operational History:** No evidence has been found that the semantic claim pipeline participated in the active runtime. There are zero archived ledgers, zero organic claims, and zero callers bridging the active input stream to the `T04`/`T05` scripts.
> 2. **Mock Ecosystem:** Every single `CLM-` reference globally traces back to either design blueprints in chat logs, explicit unit tests validating firewall logic, or the system's own internal services testing themselves against the initial `FIXTURE` entries.
>
> The semantic subsystem appears to have functioned as an experimental validation environment for epistemic and immune-boundary mechanics rather than as a production semantic metabolism. The laboratory was not empty; it was running experiments against its own fixture claims (e.g. `TRUTH-RESEARCH-001` investigating `CLM-T`). Current evidence strongly favors a laboratory/test-harness interpretation, though complete exclusion of prior integration or removed activation paths remains unproven.
