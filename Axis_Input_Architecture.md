# Axis Input Channel Architecture (v21 Extension)

## Overview
This document defines the **Asynchronous Input Channel** bridging the `Axis_Heartbeat_UI` (HTML/JS) and the sealed `Axis_Core` (PowerShell). It adheres to the "Anchor Seal" invariant: **No external interface touches the Spine directly.**

## 1. The Bridge: `UI_Inbox`
*   **Path**: `D:\infinite\Infinity\UI_Inbox\`
*   **Mechanism**: "Dropbox" pattern.
    *   **Writer**: `Axis_Heartbeat_Server.ps1` (via `POST /ui-intent`).
    *   **Reader**: `Axis_Mind.ps1` (via `Process-UIInbox` cycle).
    *   **Format**: Single JSON files per intent.

## 2. Queue Schema (`UI_Inbox/*.json`)
Files are named: `{Timestamp}-{Verb}-{Random}.json`

### Type: `trigger_chronos_pulse`
```json
{
  "version": 1,
  "source": "Axis_Heartbeat_UI",
  "created_at": "2026-01-13T21:00:00Z",
  "type": "ui_intent",
  "verb": "trigger_chronos_pulse",
  "parameters": {}
}
```

### Type: `request_drill_sim_only`
```json
{
  "version": 1,
  "source": "Axis_Heartbeat_UI",
  "created_at": "2026-01-13T21:05:00Z",
  "type": "ui_intent",
  "verb": "request_drill_sim_only",
  "parameters": {
    "tool": "ADMIN-Echo-Test",
    "reason": "Dashboard Request"
  }
}
```

## 3. Implementation Status
*   **Server**: Updated to handle `POST /ui-intent`. Writes to Inbox.
*   **Mind**: Updated with `Process-UIInbox` function.
    *   **Sanitization**: Only allows specific verbs.
    *   **Mapping**:
        *   `trigger_chronos_pulse` -> `Intent_Queue.json` (CHRONOS_PULSE).
        *   `request_drill_sim_only` -> `Requests_Queue.json` (as `ADMIN-Echo-Test`).
    *   **Gating**: Mind Loop forces `Risk: 80` + `Status: waiting_for_approval` for any `ui_origin` drill, ensuring Anchor oversight.

## 4. Invariant Check (Trust & Seal)
1.  **Input**: UI cannot write to `Requests_Queue.json`.
2.  **Gate**: `Axis_Mind` forces all UI Drills to `waiting_for_approval`.
3.  **Execution**: Only `Earth_Server` executes, subject to `Anchor Decision`.
