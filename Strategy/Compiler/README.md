# Axis Governance Capsule: Seal Clause

> **No verified contract, no verified observatory, no motion.**

This directory contains the core mission mandates and invariant configurations for the Axis agent. It is formally sealed to prevent architectural drift or unauthorized threshold modification.

### 1. Attestation Scope (Governance-Config)
The system calculates a SHA256 manifest hash of the following **configuration** files. 
- `mission_contract.v1.json` (Target weights, SLOs, Hard bounds)
- `objective_policy.v1.json` (Safety constraints, Anti-Proxy rules)
*Note: Implementation code (.py) is treated as part of the Trusted Base and is not currently hashed.*

### 2. Trusted Anchor
The manifest hash is verified against:
`D:\Infinite\Infinity\Strategy\State\trusted_digest.sha256`

**Failure Behavior**: Hard Stop on `BREACH_EMPTY_ANCHOR` or `BREACH_HASH_MISMATCH`.

### 3. Blindness Conditions
- **Metric Freshness**: If `Governance_Metrics.json` is > 1 hour stale, the agent enters a `blind` state.
- **Freeze Rules**: 
  - `StrategyEngine.simulate()`: ABORT
  - `StrategyEngine.propose()`: ABORT (Ledger Write-Lock)

### 4. Verification Command (Ergonomic)
To view current vs expected status and PASS/FAIL verdict:
```powershell
python -c "import sys, os; sys.path.append('D:\Infinite\Infinity\Strategy'); from multi_objective_solver import MultiObjectiveSolver; s = MultiObjectiveSolver('D:\Infinite\Infinity\Strategy\Compiler\mission_contract.v1.json'); anchor = os.path.join(s.state_dir, 'trusted_digest.sha256'); expected = open(anchor).read().strip(); current = s.contract_hash; res = 'PASS' if current == expected else 'FAIL'; print(f'Current Digest:  {current}\nExpected Digest: {expected}\nResult:          [{res}]')"
```

---
**Status**: ARCHIVE-GRADE SEALED (v1.2)
**Rule**: If the observatory is blind, the agent must go still.
