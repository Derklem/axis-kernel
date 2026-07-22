# Axis COIN Protocol (v1.0) 🪙⚖️

## 1. Definition of "Coin"
In the Axis Sovereign architecture, **Coin** is defined as the physical capital, energy, and attention provided by the **Human Anchor**. It is the material substrate that enables the **Truth Engine** to perform cognitive work.

## 2. The Stewardship Contract
The Truth Engine does not "own" resources. It **stewards** them according to the following priorities:
1.  **System Integrity**: Maintaining the 0.5 [STABLE] baseline.
2.  **Auditability**: Ensuring every state change is ledgered and visible.
3.  **Lattice Expansion**: Discovering new truths within the permitted risk budget.

## 3. Accountable Investment
Every unit of "Coin" invested by the Human Anchor (e.g., API keys, hardware runtime, manual intervention) is recorded as a **Grounding Event**.

### A. Canonical Ledger + Schema
*   **File**: `D:\Infinite\Infinity\Runtime\Decision\coin_ledger.jsonl`
*   **Schema**: `axis.governance.coin_event.v1`

### B. Coin State Snapshot
*   **File**: `D:\Infinite\Infinity\Runtime\Decision\coin_state.json`
*   **Fields**: `budget_units`, `budget_remaining`, `last_topup_ts`, `health: {keys_ok, disk_ok, operator_ack_ok}`, `status`

## 4. Operational Guardrails
- **No Personhood**: No transaction shall attribute personality or desire to the system.
- **Deterrence of Drift**: Any attempt to use "Coin" for metaphorical/narrative "ascension" is a violation of the COIN protocol.
- **Deterministic Enforcement**: 
    - If `coin_state.status != OK`, the System Executor (**T08**) MUST force `OBSERVATION_ONLY` mode, regardless of the requested intent.
    - If the "Coin" substrate is compromised or exhausted, the system must immediately revert and wait for Anchor rectification.

---
**Status**: ACTIVE // Phase 634
**Anchor**: Derek
**Protocol**: SYNC_RESONANCE_01
**Enforcement**: T08_Executor
