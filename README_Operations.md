# Axis Operations Runbook (v1.0)

## 0. Core Mental Model
* **Axis_Core.ps1** – Heartbeat + watchdog + intent generator.
* **Axis_Mind.ps1** – Cognition + simulation + contract gating → writes Requests_Queue.
* **Earth_Server.ps1** – Actuator. Executes *only* `status = pending` and `auto_approval = true`.
* **Approve_HighRisk.ps1** (Console) – Human review for gated requests.
* **Apply_Approvals.ps1** (Mutator) – Applies human decisions to the queue.
* **Health_Snapshot.ps1** – Single command system status check.
* **Axis_Explain_Why.ps1** – Narrative introspection.

---

## 1. Daily / Fresh Boot Sequence
After a reboot or config change:

```powershell
# 1. Start Core (if not running)
powershell -ExecutionPolicy Bypass -File D:\infinite\Axis_Core.ps1

# 2. Verify Spine (Structure)
powershell -ExecutionPolicy Bypass -File D:\infinite\Verify_Spine.ps1

# 3. Check Health (State)
powershell -ExecutionPolicy Bypass -File D:\infinite\Health_Snapshot.ps1
```

**Interpretation**:
* `PASS`: Files healthy.
* `SYSTEM GREEN`: No open incidents, no pending high-risk approvals.

---

## 2. Handling High-Risk Actions (Anchor Loop)
If `Pending Anchor > 0`:

1. **Review**: `powershell -ExecutionPolicy Bypass -File D:\infinite\Approve_HighRisk.ps1`
   * Select Index.
   * `A` (Approve), `D` (Deny), `S` (Skip).
   * Type `q` to Save & Quit.

2. **Unlock**: `powershell -ExecutionPolicy Bypass -File D:\infinite\Apply_Approvals.ps1`
   * Applies the decision to the queue.

3. **Execute**: `powershell -ExecutionPolicy Bypass -File D:\infinite\Infinity\Earth\Earth_Server.ps1`
   * Executes the pending tool.

4. **Verify**: Run `Health_Snapshot.ps1` again.

---

## 3. Incident Resolution
If `Open Incidents > 0`:

1. Copy Template: `copy D:\infinite\Resolve_Incidents_TEMPLATE.json D:\infinite\Resolve_Incidents.json`
2. Edit JSON: Set `"status": "resolved"` for the incident ID.
3. Process: `powershell -ExecutionPolicy Bypass -File D:\infinite\Axis_Mind.ps1`

---

## 4. Introspection (Explain Why)
To understand *why* something happened or is stuck:

```powershell
# Latest threads
powershell -ExecutionPolicy Bypass -File D:\infinite\Axis_Explain_Why.ps1

# Specific Request
powershell -ExecutionPolicy Bypass -File D:\infinite\Axis_Explain_Why.ps1 -RequestId "REQ-..."
```
