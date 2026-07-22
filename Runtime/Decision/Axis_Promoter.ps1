# Axis_Promoter.ps1
# Phase 27: System Promoter (Deterministic Queue)
# Reads *new* lines from an input queue (offset cursor), validates/filters, deterministically sorts,
# writes promoted queue, and archives a provenance record for verification.
#
# Files (standard):
#   Input Queue:      D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl   (or sandbox_queue.jsonl)
#   Promoted Queue:   D:\Infinite\Infinity\Runtime\Decision\promoted_queue.jsonl (or promoted_sandbox_queue.jsonl)
#   Cursor:           ...\promoter_<queue>_cursor.json
#   Archive:          ...\promoter_archive.jsonl
#   State:            ...\promoter_state.json
#   Errors:           D:\Infinite\Infinity\Memory\ledger\ingest_errors.jsonl
#
# Deterministic ordering:
#   1) expires_utc (earlier first; missing -> last)
#   2) priority   (higher first; missing -> 0)
#   3) ts_utc     (older first; missing -> last)
#   4) nonce      (lexicographic)
#
# Notes:
# - Promoter is *input stabilization*. It does NOT execute anything.
# - Archive-awareness: filters out envelopes whose nonce is already executed/failed/inflight.

param(
    [ValidateSet("intent_queue", "sandbox_queue")]
    [string]$QueueName = "intent_queue",

    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

# --- Paths ---
$Root = "D:\Infinite\Infinity"
$RuntimeDir = Join-Path $Root "Runtime\Decision"

$QueueFile = Join-Path $RuntimeDir ($QueueName + ".jsonl")

$PromotedQueueFile = if ($QueueName -eq "sandbox_queue") {
    Join-Path $RuntimeDir "promoted_sandbox_queue.jsonl"
}
else {
    Join-Path $RuntimeDir "promoted_queue.jsonl"
}

$CursorFile = Join-Path $RuntimeDir ("promoter_{0}_cursor.json" -f $QueueName)
$ArchiveFile = Join-Path $RuntimeDir "promoter_archive.jsonl"
$StateFile = Join-Path $RuntimeDir "promoter_state.json"

$IngestErrors = Join-Path $Root "Memory\ledger\ingest_errors.jsonl"

$ExecutionStateFile = Join-Path $RuntimeDir "execution_state.json"

# --- Helpers ---
function New-Sha256Hex([string]$s) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
    $hash = $sha.ComputeHash($bytes)
    return ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Write-JsonlLine([string]$path, $obj) {
    if ($DryRun) { return }
    if (Get-Command Append-JsonlLineNoBom -ErrorAction SilentlyContinue) {
        Append-JsonlLineNoBom -Path $path -Data $obj
    }
    else {
        # Fallback (though FS_Lib should be loaded)
        $line = ($obj | ConvertTo-Json -Compress -Depth 20)
        $line | Add-Content -Path $path -Encoding UTF8
    }
}

function Load-Json([string]$path, $defaultObj) {
    if (-not (Test-Path $path)) { return $defaultObj }
    try { return (Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json) }
    catch { return $defaultObj }
}

function Save-Json([string]$path, $obj) {
    if ($DryRun) { return }
    if (Get-Command Write-AtomicJson -ErrorAction SilentlyContinue) {
        Write-AtomicJson -Path $path -Data $obj
    }
    else {
        $obj | ConvertTo-Json -Depth 20 | Set-Content -Path $path -Encoding UTF8 -Force
    }
}

function Parse-IsoUtcOrNull([string]$s) {
    if ([string]::IsNullOrWhiteSpace($s)) { return $null }
    try {
        # Accept DateTimeOffset strings; normalize to UTC DateTime for stable comparisons
        return [DateTimeOffset]::Parse($s).ToUniversalTime().UtcDateTime
    }
    catch { return $null }
}

function Get-ExecutionArchiveSet {
    # Build a HashSet of nonces that should not be re-promoted.
    $set = New-Object 'System.Collections.Generic.HashSet[string]'
    if (-not (Test-Path $ExecutionStateFile)) { return $set }

    try {
        $s = Get-Content $ExecutionStateFile -Raw -Encoding UTF8 | ConvertFrom-Json

        # executed_intents / failed_intents are arrays
        if ($s.executed_intents) {
            foreach ($x in $s.executed_intents) { [void]$set.Add([string]$x) }
        }
        if ($s.failed_intents) {
            foreach ($x in $s.failed_intents) { [void]$set.Add([string]$x) }
        }

        # inflight is a dictionary-ish object -> keys are nonces
        if ($s.inflight) {
            if ($s.inflight -is [System.Management.Automation.PSCustomObject]) {
                foreach ($p in $s.inflight.PSObject.Properties) { [void]$set.Add([string]$p.Name) }
            }
            elseif ($s.inflight -is [System.Collections.IDictionary]) {
                foreach ($k in $s.inflight.Keys) { [void]$set.Add([string]$k) }
            }
        }
    }
    catch {
        # If state is unreadable, fail-closed by returning what we have (empty) and logging.
        $err = [ordered]@{
            ts_utc     = (Get-Date).ToUniversalTime().ToString("o")
            event_type = "promoter_state_read_failed"
            file       = $ExecutionStateFile
            error      = $_.Exception.Message
        }
        Write-JsonlLine $IngestErrors $err
    }

    return $set
}

function Read-NewQueueLines {
    # Offset cursor reader (like executor), but returns raw lines + metadata so we can sha-bind.
    $cursorDefault = [ordered]@{
        schema      = "axis.promoter_cursor.v0.1"
        queue       = $QueueName
        source      = $QueueFile
        byte_offset = 0
        line        = 0
        ts_utc      = $null
        file_len    = 0
        file_time   = $null
    }
    $cursor = Load-Json $CursorFile $cursorDefault

    $result = [ordered]@{
        cursor_before = $cursor
        cursor_after  = $cursor
        lines         = @()  # each: { line_no, raw, sha256 }
        file_len      = 0
        file_time     = $null
        truncated     = $false
        abort_batch   = $false
    }

    if (-not (Test-Path $QueueFile)) { return $result }

    $item = Get-Item $QueueFile
    $result.file_len = $item.Length
    $result.file_time = $item.LastWriteTimeUtc.ToString("o")

    $newOffset = [int64]$cursor.byte_offset
    $newLineNo = [int]$cursor.line

    $fs = $null
    $reader = $null
    try {
        $fs = [System.IO.File]::Open($QueueFile, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        $reader = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8)

        # Truncation handling
        if ($newOffset -gt $fs.Length) {
            $result.truncated = $true
            $newOffset = 0
            $newLineNo = 0
        }

        if ($newOffset -gt 0) {
            $fs.Seek($newOffset, [System.IO.SeekOrigin]::Begin) | Out-Null
            $reader.DiscardBufferedData()
        }

        while (-not $reader.EndOfStream) {
            $raw = $reader.ReadLine()
            if ($null -eq $raw) { break }

            # If we fail parsing later, we still want deterministic sha binding to this exact line
            $sha = "sha256:" + (New-Sha256Hex $raw)
            $newLineNo++

            $result.lines += [pscustomobject]@{
                line_no = $newLineNo
                raw     = $raw
                sha256  = $sha
            }
        }

        $newOffset = $fs.Position
    }
    catch {
        # If we were at EOF and got partial write, we can be conservative:
        $result.abort_batch = $true
        $err = [ordered]@{
            ts_utc     = (Get-Date).ToUniversalTime().ToString("o")
            event_type = "promoter_queue_read_error"
            queue      = $QueueName
            file       = $QueueFile
            error      = $_.Exception.Message
        }
        Write-JsonlLine $IngestErrors $err
    }
    finally {
        if ($reader) { $reader.Dispose() }
        if ($fs) { $fs.Dispose() }
    }

    if (-not $result.abort_batch) {
        $result.cursor_after = [ordered]@{
            schema      = $cursor.schema
            queue       = $QueueName
            source      = $QueueFile
            byte_offset = $newOffset
            line        = $newLineNo
            ts_utc      = (Get-Date).ToUniversalTime().ToString("o")
            file_len    = $result.file_len
            file_time   = $result.file_time
        }
    }

    return $result
}

function Persist-Cursor($cursorAfter) {
    if ($DryRun) { return }
    Save-Json $CursorFile $cursorAfter
}

function Extract-EnvelopeFromLine($obj) {
    # Supports:
    # - direct v2 envelope line: { schema="axis.intent_envelope.v2", nonce, identity, key_id, intent_json, signature, ... }
    # - wrapped: { envelope: { ... } }
    if ($null -eq $obj) { return $null }
    try {
        if ($obj.schema -and ([string]$obj.schema -like "axis.intent_envelope.*")) { return $obj }
        if ($obj.envelope) { return $obj.envelope }
    }
    catch {}
    return $null
}

# --- Build ---
$PromoterBuild = if ($PSCommandPath) { (Get-Item $PSCommandPath).LastWriteTimeUtc.ToString("yyyyMMdd-HHmmss") } else { "Unknown" }
$RunId = "PROM-" + (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss") + "-" + (New-Guid).ToString("N").Substring(0, 8)
$ScanTs = (Get-Date).ToUniversalTime().ToString("o")

# --- Read new lines ---
$read = Read-NewQueueLines
$linesSeen = $read.lines.Count

# Persist cursor early (exactly-once line consumption). If read aborted, do not advance.
if ($read.truncated) {
    $evt = [ordered]@{
        ts_utc     = $ScanTs
        event_type = "promoter_queue_truncated_reset"
        queue      = $QueueName
        file       = $QueueFile
        old_offset = $read.cursor_before.byte_offset
        new_offset = 0
    }
    Write-JsonlLine $ArchiveFile $evt
}

if (-not $read.abort_batch) {
    Persist-Cursor $read.cursor_after
}

# --- Load archive-awareness set ---
$blockedNonces = Get-ExecutionArchiveSet

# --- Process / validate / stage candidates ---
$candidates = @()
$valid = 0
$invalid = 0
$skippedArchived = 0

$oldestTs = $null
$newestTs = $null

foreach ($l in $read.lines) {
    $raw = $l.raw

    if ([string]::IsNullOrWhiteSpace($raw)) { continue }

    $obj = $null
    try {
        $obj = $raw | ConvertFrom-Json
    }
    catch {
        $invalid++
        $err = [ordered]@{
            ts_utc      = $ScanTs
            event_type  = "ingest_error"
            subsystem   = "promoter"
            queue       = $QueueName
            reason      = "JSON_PARSE_ERROR"
            line_no     = $l.line_no
            line_sha256 = $l.sha256
            raw         = $raw
        }
        Write-JsonlLine $IngestErrors $err
        continue
    }

    $env = Extract-EnvelopeFromLine $obj
    if (-not $env) {
        $invalid++
        $err = [ordered]@{
            ts_utc      = $ScanTs
            event_type  = "ingest_error"
            subsystem   = "promoter"
            queue       = $QueueName
            reason      = "MISSING_ENVELOPE"
            line_no     = $l.line_no
            line_sha256 = $l.sha256
            raw         = $raw
        }
        Write-JsonlLine $IngestErrors $err
        continue
    }

    # Minimal envelope fields for promotion determinism
    $nonce = [string]$env.nonce
    if ([string]::IsNullOrWhiteSpace($nonce)) {
        $invalid++
        $err = [ordered]@{
            ts_utc      = $ScanTs
            event_type  = "ingest_error"
            subsystem   = "promoter"
            queue       = $QueueName
            reason      = "MISSING_NONCE"
            line_no     = $l.line_no
            line_sha256 = $l.sha256
            raw         = $raw
        }
        Write-JsonlLine $IngestErrors $err
        continue
    }

    if ($blockedNonces.Contains($nonce)) {
        $skippedArchived++
        # Archive the skip (for verifier / operator visibility)
        $evt = [ordered]@{
            ts_utc      = $ScanTs
            event_type  = "promoter_skip_archived"
            queue       = $QueueName
            nonce       = $nonce
            line_no     = $l.line_no
            line_sha256 = $l.sha256
            reason      = "EXECUTED_FAILED_OR_INFLIGHT"
            run_id      = $RunId
            build       = $PromoterBuild
        }
        Write-JsonlLine $ArchiveFile $evt
        continue
    }

    # Extract deterministic sort keys
    $expires = Parse-IsoUtcOrNull ([string]$env.expires_utc)
    $tsUtc = Parse-IsoUtcOrNull ([string]$env.ts_utc)

    # Optional priority: can exist on envelope or embedded intent json
    $priority = 0
    try {
        if ($env.priority -ne $null) { $priority = [int]$env.priority }
        elseif ($env.intent_json) {
            $ij = $env.intent_json | ConvertFrom-Json
            if ($ij.priority -ne $null) { $priority = [int]$ij.priority }
        }
    }
    catch { $priority = 0 }

    # Track pending range (for heartbeat)
    if ($null -ne $tsUtc) {
        if (-not $oldestTs -or $tsUtc -lt $oldestTs) { $oldestTs = $tsUtc }
        if (-not $newestTs -or $tsUtc -gt $newestTs) { $newestTs = $tsUtc }
    }

    $valid++

    $candidates += [pscustomobject]@{
        nonce              = $nonce
        expires_dt_utc     = $expires
        ts_dt_utc          = $tsUtc
        priority           = $priority
        envelope           = $env
        line_no            = $l.line_no
        source_line_sha256 = $l.sha256
        raw_line_sha256    = $l.sha256
    }
}

# --- Deterministic sort ---
# missing dates are sorted last by using a max sentinel
$maxDt = [DateTime]::MaxValue

$sorted = $candidates | Sort-Object `
@{ Expression = { if ($_.expires_dt_utc) { $_.expires_dt_utc } else { $maxDt } }; Ascending = $true }, `
@{ Expression = { $_.priority }; Descending = $true }, `
@{ Expression = { if ($_.ts_dt_utc) { $_.ts_dt_utc } else { $maxDt } }; Ascending = $true }, `
@{ Expression = { $_.nonce }; Ascending = $true }

# --- Write promoted items + archive records ---
$promotedCount = 0
foreach ($c in $sorted) {
    $promoted = [ordered]@{
        schema             = "axis.promoted_envelope.v0.1"
        promoted_ts_utc    = $ScanTs
        promoter_run_id    = $RunId
        promoter_build     = $PromoterBuild
        queue              = $QueueName
        nonce              = $c.nonce
        source_line_sha256 = $c.source_line_sha256
        envelope           = $c.envelope
        sort_keys          = [ordered]@{
            expires_utc = if ($c.expires_dt_utc) { $c.expires_dt_utc.ToString("o") } else { $null }
            priority    = $c.priority
            ts_utc      = if ($c.ts_dt_utc) { $c.ts_dt_utc.ToString("o") } else { $null }
            nonce       = $c.nonce
        }
    }

    if (-not $DryRun) {
        if (Get-Command Append-JsonlLineNoBom -ErrorAction SilentlyContinue) {
            Append-JsonlLineNoBom -Path $PromotedQueueFile -Data $promoted
        }
        else {
            ($promoted | ConvertTo-Json -Compress -Depth 50) | Add-Content -Path $PromotedQueueFile -Encoding UTF8
        }
    }

    $promotedCount++

    $evt = [ordered]@{
        ts_utc      = $ScanTs
        event_type  = "promoter_promoted"
        queue       = $QueueName
        nonce       = $c.nonce
        line_no     = $c.line_no
        line_sha256 = $c.source_line_sha256
        promoted_to = $PromotedQueueFile
        run_id      = $RunId
        build       = $PromoterBuild
        sort_keys   = $promoted.sort_keys
    }
    Write-JsonlLine $ArchiveFile $evt
}

# --- State / Metrics (for Drift Heartbeat) ---
$state = [ordered]@{
    schema              = "axis.promoter_state.v0.1"
    ts_utc              = $ScanTs
    run_id              = $RunId
    build               = $PromoterBuild
    queue               = $QueueName
    input_queue_file    = $QueueFile
    promoted_queue_file = $PromotedQueueFile
    cursor_file         = $CursorFile
    archive_file        = $ArchiveFile

    scan                = [ordered]@{
        file_len        = $read.file_len
        file_time       = $read.file_time
        truncated_reset = $read.truncated
        abort_batch     = $read.abort_batch
    }

    counts              = [ordered]@{
        lines_seen        = $linesSeen
        valid_envelopes   = $valid
        invalid_envelopes = $invalid
        skipped_archived  = $skippedArchived
        promoted_count    = $promotedCount
    }

    pending_range       = [ordered]@{
        oldest_ts_utc = if ($oldestTs) { $oldestTs.ToString("o") } else { $null }
        newest_ts_utc = if ($newestTs) { $newestTs.ToString("o") } else { $null }
    }
}

Save-Json $StateFile $state

Write-Host ("[PROMOTER] queue={0} seen={1} valid={2} invalid={3} skipped_archived={4} promoted={5} run={6}" -f `
        $QueueName, $linesSeen, $valid, $invalid, $skippedArchived, $promotedCount, $RunId) -ForegroundColor Cyan
