# README: The Agency Spine (v17.0 - Entanglement Seal)

**The Sovereign Lattice Architecture.**
This document is the **Canonical Source of Truth** for the Axis Environment.
**Status**: SEALED. No new actuation behaviors without updating this spec.

---

## 1. Core Principles
1.  **Fail Closed**: If Simulation fails or Risk is high, action is Denied.
2.  **Double ID**: Every Act (Earth) must link to an Intent (Request).
3.  **Hygiene**: `Glassworm` ensures bounded history; nothing grows forever.
4.  **Resilience**: `Axis_Core` watchdogs ensure the Lattice breathes.

---

## 2. The Artifact Spine (Data Flow)

### A. Intent Queue (Cognition)
*   **Path**: `D:\infinite\Intent_Queue.json`
*   **Owner**: `Axis_Core.ps1` (Writer), `Axis_Mind.ps1` (Reader).
*   **Purpose**: Triggers (`CHRONOS_PULSE`, `VISUAL_CONTACT`).

### B. Simulation Trace (Prediction) (v14)
*   **Path**: `D:\infinite\Infinity\Sim_Trace.json`
*   **Owner**: `Sim_Engine.ps1`
*   **Schema**:
    ```json
    { "simulations": [{ "id": "SIM-...", "risk_score": 80, "recommendation": "Block" }] }
    ```

### C. Requests Queue (Gating) (v15)
*   **Path**: `D:\infinite\Infinity\Earth\Requests_Queue.json`
*   **Owner**: `Axis_Mind.ps1`
*   **Status Enum**: `pending` (Safe), `waiting_for_approval` (Gated), `denied` (Blocked), `completed`, `failed`.
*   **Schema**:
    ```json
    { "requests": [{ 
        "id": "REQ-...", 
        "tool": "Read-File", 
        "sim_data": { "risk_score": 10 }, 
        "status": "pending",
        "gate_note": "Risk 10 < 20"
    }]}
    ```

### D. Earth Log (Actuation) (v16.1)
*   **Path**: `D:\infinite\Infinity\Earth\Earth_Log.json`
*   **Owner**: `Earth_Server.ps1`
*   **Invariant**: Must include `request_id`.
*   **Schema**:
    ```json
    { "history": [{ 
        "id": "EARTH-...", 
        "request_id": "REQ-...", 
        "tool": "Read-File", 
        "status": "completed" 
    }]}
    ```

### E. Entanglement Index (Narrative) (v16.0)
*   **Path**: `D:\infinite\Infinity\Entanglement_Index.json`
*   **Owner**: `Entangle.ps1`
*   **Purpose**: Links Sim -> Req -> Earth.
*   **Schema**:
    ```json
    { "threads": [{ 
        "id": "THREAD-...", 
        "sim_id": "SIM-...", 
        "request_id": "REQ-...", 
        "earth_action_id": "EARTH-..." 
    }]}
    ```

---

## 3. The Agents

### 1. Axis_Core (The Supervisor) (v16.2)
*   **Role**: Process Watchdog & Link Monitor.
*   **Loop**: 60 seconds.
*   **Behavior**:
    *   Monitors Router/Constellation.
    *   Checks Timestamps of `Mind`, `Earth`, `Glassworm`, `Entangle`.
    *   **Remediates**: Auto-starts `Glassworm`/`Entangle` if stale > 24h.
    *   **Alerts**: Logs incident if `Mind`/`Earth` stale > 15m.

### 2. Axis_Mind (The Cortex)
*   **Role**: Analysis & Decision using `Autonomy_Contract.json`.
*   **Behavior**: Simulation -> Gating -> Request.

### 3. Glassworm (The Janitor)
*   **Role**: Memory Hygiene.
*   **Behavior**: Archives logs > 50/100 items to `Archives/`.

### 4. Entangle (The Scribe)
*   **Role**: Quantum Narrative.
*   **Behavior**: Scans logs, builds Threads.

---

### 5. Approvals (Anchor Layer) (v18.0)
*   **Path**: `D:\infinite\Infinity\Approvals.json`
*   **Owner**: `Approve_HighRisk.ps1` (Writer), `Apply_Approvals.ps1` (Reader).
*   **Purpose**: Human manual authorization for `waiting_for_approval` requests.

---

**Validated By**: `Verify_Spine.ps1` (v18)
