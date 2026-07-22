## Axis Mind v12.0 — Fusion Engine Design (Draft)

**Identity:** Axis-Self-Recursive-001
**Mode:** Design / Fusion Epoch
**Author:** Axis_Mind.ps1 (with external advisor)

---

### 1. Purpose

The Fusion Engine exists to solve a specific limitation in v2–v11:

> The system perceives **events per channel** (Constellation, Retina, Router, Incidents) but does not reason over **episodes** that span multiple channels and time.

**Goal of v12.0:**
Introduce a **multi-modal fusion layer** that:

1. Aligns events from different channels into **Fusion Episodes** on a unified timeline.
2. Exposes these episodes to:

   * CHRONOS_PULSE (dashboard)
   * The Policy/Pattern engines (later)
   * Future Simulation Engine (v13.0).

v12.0 remains **read-only**: no new actuation, only synthesis and logging.

---

### 2. Data Sources (Inputs)

All fusion operates over a sliding time window (default: last 7 days).

* **Constellation / Nodes**

  * `D:\infinite\Infinity\Constellation_Index.json`
  * Fields used:

    * `nodes[].ip`
    * `nodes[].label`
    * `nodes[].trust`
    * `nodes[].first_seen`
    * `nodes[].last_seen`
    * `nodes[].status`
    * `nodes[].missing_since`
    * `nodes[].concern`

* **Incidents**

  * `D:\infinite\Infinity\Incident_Log.json`
  * Fields used:

    * `incidents[].id`
    * `incidents[].timestamp`
    * `incidents[].type`
    * `incidents[].severity`
    * `incidents[].status`
    * `incidents[].context` (including `ip`, `label`, `source`, etc.)
    * `incidents[].recommended_actions`

* **Router History**

  * `D:\infinite\Infinity\Router_Status_History.json`
  * Fields used:

    * `history[].timestamp`
    * `history[].details` (any structured router state / failure info)

* **Retina Events**

  * `D:\infinite\Retina\visual_events.json`
  * Fields used:

    * `events[].id`
    * `events[].timestamp`
    * `events[].severity_guess`
    * `events[].category`
    * `events[].summary`
    * `events[].details`
    * `events[].handled` (for correlation we only need timestamp + metadata)

* **Config**

  * `D:\infinite\Axis_Config.json`
  * New / used fields:

    * `patterns.window_days` (already present)
    * New (optional): `fusion.correlation_window_minutes` (default: `5`)

---

### 3. New Artifact: Fusion Timeline

**Path**

```text
D:\infinite\Infinity\Fusion_Timeline.json
```

**Schema (v1)**

```jsonc
{
  "version": 1,
  "window_days": 7,
  "last_generated": "2026-01-12T11:59:59Z",
  "correlation_window_minutes": 5,
  "episodes": [
    {
      "id": "EP-20260112-120001-001",
      "start": "2026-01-12T10:58:51Z",
      "end": "2026-01-12T11:03:51Z",
      "severity": "warning",          // max of participating elements
      "tags": ["visual", "network"],  // channel tags
      "summary": "Visual anomaly coinciding with router instability.",
      "nodes": [
        {
          "ip": "192.168.1.6",
          "label": "UNKNOWN_192-168-1-6",
          "trust": "unclassified",
          "role": "unknown",
          "involvement": ["incident", "constellation"]
        }
      ],
      "incidents": [
        {
          "id": "20260112-105851-visual_anomaly",
          "type": "visual_anomaly",
          "severity": "warning"
        }
      ],
      "visual_events": [
        {
          "id": "TEST-VISUAL-001",
          "category": "anomaly",
          "severity_guess": "warning",
          "summary": "Test visual anomaly for Axis Mind v8.0."
        }
      ],
      "router_events": [
        {
          "timestamp": "2026-01-12T10:59:12Z",
          "summary": "Critical link loss.",
          "details_ref": "inline or compact"
        }
      ],
      "meta": {
        "channel_count": 2,
        "incident_count": 1,
        "visual_count": 1,
        "router_count": 0,
        "has_trusted_node": false
      }
    }
  ]
}
```

Notes:

* `episodes[*].severity` = max(severity of incidents + mapped visual severity).
* `tags` = simple labels: `["constellation"]`, `["visual"]`, `["visual","network"]`, etc.
* v12.0: **no back-references** from source logs; Fusion_Timeline is *derived*, not authoritative.

---

### 4. Correlation Logic

New function (conceptual):

```powershell
function Build-FusionTimeline {
    param(
        $incidents,
        $routerHistory,
        $visualEvents,
        $constellationIndex,
        $windowDays,
        $correlationMinutes
    )
}
```

#### 4.1 Time Window

* `windowDays` = `Config.patterns.window_days` (fallback: `7`).
* `since = Now - windowDays`.

Filter:

* `$recentIncidents = incidents where timestamp >= since`
* `$recentRouter = history where timestamp >= since`
* `$recentVisuals = events where timestamp >= since`
* Constellation is *snapshot-like*, not event log; we use it to annotate nodes, not to drive episodes.

#### 4.2 Base Units: Seeds

Every **incident** becomes a potential **episode seed**:

* `seedTime = incident.timestamp`
* Episode time span: `[seedTime - Δ, seedTime + Δ]`, where `Δ = correlation_window_minutes`.

We then **attach correlated events**:

* Visual events where `|visual.timestamp - seedTime| <= Δ`
* Router history entries where `|router.timestamp - seedTime| <= Δ`
* Nodes from `Constellation_Index` referenced in incident context or matching IPs.

Optionally, we may also create episodes seeded by visual events with no incident, but in v12.0 it is enough to:

> seed = incidents
> attach = visual + router + node metadata

#### 4.3 Episode Construction

For each seed incident `i`:

1. Collect:

   * `relatedVisuals`
   * `relatedRouterEvents`
   * `relatedNodes` (from `i.context.ip` / `i.context.label`)
2. Compute:

   * `episodeSeverity = max(incident.severity, mappedVisualSeverity)`
   * `tags`:

     * include `"visual"` if any visualEvents
     * include `"network"` if any routerEvents or type `critical_link_loss`
     * include `"node:<ip>"` for each involved node
3. Compute `start` and `end` as min / max timestamp over all participants (or `seedTime ± Δ` if single).

Append to `episodes[]`.

#### 4.4 Visual Severity Mapping

Simple mapping:

* if `visual.severity_guess in ["critical","alert","warning"]` → same
* else → `"info"`

Episode severity:

* Map incident severity to order: `info < warning < alert < critical`
* Take max over:

  * incident.severity
  * mapped visual severity (if any)

---

### 5. Integration Points in Axis_Mind.ps1 (v12.0)

**New Config Block (optional)**

```jsonc
"fusion": {
  "correlation_window_minutes": 5
}
```

**New helper functions:**

* `Load-FusionTimeline` / `Save-FusionTimeline`
* `Build-FusionTimeline` (as described)
* `Summarize-FusionForDashboard` (produces a few human-readable lines)

**Where it runs:**

Inside `Process-ChronosPulse`:

1. Load incidents, router history, visual log, constellation index.
2. Call `Build-FusionTimeline`.
3. Save to `Fusion_Timeline.json`.
4. Add new section to CHRONOS prompt:

Example:

```text
--- FUSION EPISODES (Last 7d) ---
Total Episodes: 1
  - EP-20260112-120001-001 | severity: warning | channels: visual, network
    Nodes: UNKNOWN_192-168-1-6
    Incidents: 1 (visual_anomaly)
```

v12.0 does **not** change:

* Policy suggestion generation
* Incident logging
* Actions staging

It only **enriches** the dashboard & data.

---

### 6. Failure Modes & Safety

v12.0 must **fail soft**:

* If any upstream JSON is missing or malformed:

  * Log `"[FUSION] WARN"` and skip fusion.
  * Do not crash CHRONOS_PULSE.
* If no incidents exist in the window:

  * Fusion_Timeline.json is updated with:

    * `episodes: []`
    * `summary.total_incidents = 0`
  * Dashboard prints:

    ```text
    --- FUSION EPISODES (Last 7d) ---
    No fused episodes (insufficient incident data).
    ```

No code in v12.0 changes:

* `Axis_Config.json`
* `Constellation_Index.json`
* External systems

It is **pure analysis**.

---

### 7. Relationship to v13.0 and v14.0

* **v13.0 (Simulation Engine)** will read from:

  * `Fusion_Timeline.json`
  * `Risk_Patterns.json`
  * `Policy_Suggestions.json`

  to run “what-if” scenarios over **episodes**, not raw events.

* **v14.0 (Autonomy Contract)** will define:

  * Which patterns + policies + episode types are permitted to trigger auto-changes.
  * Constraints on *where* and *how often* those changes can occur.

v12.0’s only obligation is to provide a **clean, stable representation of episodes** so later epochs can reason about the world as **joined experiences**, not isolated logs.
