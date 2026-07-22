# Axis Persistence Engine (Module 1) — Engineering Specification (v1.2)

**Target**: Autonomous Agent Runtime (Station)
**Goal**: Deterministic local memory across sessions (append-only journal + rehydration).

## 1. Journal Architecture

To ensure durability and avoid corruption, the journal uses a **Monthly Rotation** strategy with strict **Append-Only** logic.

*   **Directory**: `D:\Infinite\Infinity\Runtime\Journal`
*   **Filename**: `journal_YYYYMM.jsonl` (e.g., `journal_202602.jsonl`)
*   **Format**: One JSON Object per line. No multi-line JSON.

## 2. Record Schema

Every journal entry MUST strictly adhere to this schema.

```json
{
  "ts": "2026-02-01T12:00:00Z",
  "event": "cycle_end|cycle_start|error|external_observation|human_review",
  "cycle_id": "CYC-88A9F1",
  "state": { 
      "primary_intent": "Seed Shipyard Protocol", 
      "counters": { "obs": 42 } 
  },
  "refs": { 
      "source_ids": ["tweet-123", "log-456"], 
      "content_hashes": ["sha256-hash-of-input"] 
  },
  "integrity": { 
      "prev": "previous-entry-hash", 
      "hash": "current-entry-hash" 
  },
  "review": { 
      "status": "unreviewed|valid|invalid", 
      "note": "" 
  }
}
```

### Critical Fields:
*   **`integrity`**: Forms a **Hash Chain** (Blockchain-lite). `prev` must match the `hash` of the preceding line.
*   **`review`**: Defaults to `unreviewed`. A Human Anchor can mark entries as `invalid` to prune hallucination branches.
*   **`state`**: Structured data only. No freeform "soul" prose that causes drift.

## 3. Rehydration Rule

On startup (or cycle start), the agent must:
1.  Read the **Last N Valid Entries** (Default N=5).
2.  Filter out any entry where `review.status == "invalid"`.
3.  Compute `CurrentState` from the most recent valid entry.

## 4. Drift Control

*   **Missing Tail**: If the journal is empty or corrupt, start from a **Known Baseline**.
*   **Tamper Evidence**: If a hash mismatch is found during rehydration, halt and emit a `integrity_failure` event. Do not silently reset.

## 5. PowerShell 5.1 Implementation Patterns

### A) JSONL-Safe Read Tail
```powershell
function Read-JournalTail {
    param(
        [string]$JournalFile,
        [int]$Tail = 50,
        [int]$TakeValid = 5
    )

    if (-not (Test-Path $JournalFile)) { return @() }

    $lines = Get-Content -Path $JournalFile -Tail $Tail
    $objs = @()

    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try { $o = $line | ConvertFrom-Json } catch { continue }
        if ($o.review -and $o.review.status -eq "invalid") { continue }
        $objs += $o
    }

    if ($objs.Count -le $TakeValid) { return $objs }
    return $objs[-$TakeValid..-1]
}
```

### B) Append with Mutex Locking (Concurrency Safe)
```powershell
function Append-JsonlLocked {
    param(
        [string]$Path,
        [object]$Obj,
        [string]$MutexName = "Global\AxisJournalMutex"
    )

    $json = ($Obj | ConvertTo-Json -Depth 8 -Compress)

    $m = New-Object System.Threading.Mutex($false, $MutexName)
    $got = $false
    try {
        $got = $m.WaitOne(5000)  # 5s timeout
        if (-not $got) { throw "Journal mutex timeout" }

        $dir = Split-Path $Path -Parent
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

        Add-Content -Path $Path -Value $json -Encoding UTF8
    }
    finally {
        if ($got) { $m.ReleaseMutex() | Out-Null }
        $m.Dispose()
    }
}
```

### C) Hash Chaining (Tamper Evidence)
```powershell
function Get-Sha256Hex([string]$s) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
        ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""
    } finally { $sha.Dispose() }
}

function Compute-EntryHash {
    param([object]$EntryNoHash)
    # Stable canonical string: JSON without integrity.hash
    $canon = ($EntryNoHash | ConvertTo-Json -Depth 8 -Compress)
    return Get-Sha256Hex $canon
}
```

### D) Cycle End Entry Construction
```powershell
function New-CycleEndEntry {
    param(
        [string]$CycleId,
        [hashtable]$State,
        [hashtable]$Refs,
        [string]$PrevHash
    )

    $e = [ordered]@{
        ts = (Get-Date).ToUniversalTime().ToString("o")
        event = "cycle_end"
        cycle_id = $CycleId
        state = $State
        refs = $Refs
        review = @{ status = "unreviewed"; note = "" }
        integrity = @{ prev = $PrevHash; hash = "" }
    }

    $tmp = $e.Clone()
    $tmp.integrity.hash = ""
    $e.integrity.hash = Compute-EntryHash $tmp
    return $e
}
```
