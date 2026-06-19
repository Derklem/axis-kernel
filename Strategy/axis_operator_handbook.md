# Axis Operator Handbook

Welcome to the Axis Governance System. This system acts as a constitutional enforcement layer for your codebase, evaluating changes for semantic risk and enforcing immutability via a localized ledger mechanism.

The Axis operates through a **Pre-Commit Hook** and an **Advisory CI Check**. It observes code changes and uses LLM-based reasoning (via the Receptor Pipeline) to either ACCEPT or QUARANTINE those changes based on defined system invariants and limits.

---

## 1. Quick Start & Daily Usage

### The Golden Rule
**If a commit passes, Axis remains completely silent.** 
You will not see output unless Axis identifies a violation (Quarantine) or the session burden exceeds safe limits (Distress).

### Checking Status
Use the Operator Console to gain insight into the governance ledger:
```bash
# View overall system health, debt score, and session burden
python Strategy/receptor_console.py --status

# View the 5 most recent constitutional cases
python Strategy/receptor_console.py --last 5
```

### Dealing with Quarantines
If a commit is quarantined, the pre-commit hook will block the commit. The system will display the quarantine reason.
**Option 1 (Recommended): Multi-Auditor Consensus**
Run the receptor pipeline explicitly with `--audit` to solicit verdicts from registered multi-model auditors.
```bash
python Strategy/receptor_pipeline.py --check-diff .git/phase_staged.diff --audit
```
If the multi-auditor consensus accepts the change, the quarantine is resolved and you can commit successfully.

**Option 2 (Human Override): Adjudication**
If you disagree with the quarantine and the auditors, you can adjudicate the case with a physical signature (HMAC verified).
```bash
python Strategy/receptor_pipeline.py --adjudicate-quarantine <CASE_ID> --evidence-hash <HASH> --ruling ACCEPT --signature <SIG>
```

**Option 3 (Bypass): Force Commit**
You can bypass the local pre-commit hook entirely:
```bash
git commit --no-verify
```
*Note*: Bypassing the local hook does not add an acceptance receipt to the ledger. CI will still block the PR if the quarantine remains unresolved on the ledger.

---

## 2. Recovery & Debt Resolution

When changes bypass the hook or accumulate semantic drift, they generate **Constitutional Debt**. The Axis tracks this debt until it is recovered.

### Viewing Debt
```bash
# View all actionable open quarantines and their recovery states
python Strategy/receptor_console.py --debt-map

# View specific recovery proposals that are ready to apply
python Strategy/receptor_console.py --recoveries
```

### The Recovery Workflow
1. **Propose a Recovery:** Generate a patch that resolves the quarantined drift.
   ```bash
   python Strategy/receptor_pipeline.py --propose-recovery <CASE_ID> path/to/recovery.patch
   ```
2. **Apply the Recovery:** If the proposal is marked as `ELIGIBLE`, a human operator can explicitly apply it.
   ```bash
   python Strategy/receptor_pipeline.py --apply-recovery <CASE_ID> --force-apply
   ```
   This mutates the filesystem. The system will then automatically verify the application via a dry-run check.

---

## 3. Extending the Axis (Adding Auditors)

Axis uses a **Multi-Auditor Doctrine**. When primary models encounter ambiguity, other configured models are queried to form a consensus.

1. Create a new adapter in `Strategy/auditors/` that implements the standard signature:
   `def evaluate_diff(diff_content: str, previous_context: dict) -> dict:`
2. The adapter must return a dictionary including `verdict` (ACCEPT/QUARANTINE) and `confidence` (0.0 to 1.0).
3. Update the `Strategy/auditors/auditor_registry.json` to map the new auditor name to the new script.

---

## 4. Troubleshooting

**"Invariant Failed" during Replay**
This occurs when the localized ledger has been manually edited, or an event was recorded out of sequential order.
**Solution**: Check the case ID in the console (`python Strategy/receptor_console.py --case <CASE_ID>`). Never manually edit `State/receptor_ledger.jsonl`.

**Hook Always Printing "BLOCKED" Even After Edit**
Make sure you actually staged your edited files (`git add <file>`). The receptor pipeline evaluates the cached diff, not the working tree.

**CI Fails But Local Passes**
CI environments read from the committed ledger. If you used `--no-verify` to bypass local checks, your ledger has an unresolved QUARANTINE for those files. You must propose and apply a recovery, or adjudicate the quarantine, and commit that state.
