[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity",
    [string]$LogPath = "D:\Infinite\Infinity\Runtime\Decision\drift_heartbeat.jsonl"
)

$ErrorActionPreference = "Continue"

$verifier = Join-Path $Root "Runtime\Decision\Verifier\Axis_Verify_All.ps1"
$capsule = Join-Path $Root "Governance\Sovereign_State_Capsule.json"
$T08_Log = Join-Path $Root "Runtime\Decision\t08_direct_output.log"

function Sha256Tag([string]$p) {
    if (-not (Test-Path $p)) { return $null }
    "sha256:" + (Get-FileHash -Path $p -Algorithm SHA256).Hash.ToUpper()
}

$ts = (Get-Date).ToUniversalTime().ToString("o")

$exitCode = 999
$out = @()
try {
    $out = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verifier 2>&1
    $exitCode = $LASTEXITCODE
}
catch {
    $out = @($_.Exception.Message)
    $exitCode = 998
}

# parse AXIS_VERIFY_RESULT if present
$failures = $null; $warnings = $null
foreach ($line in $out) {
    if ($line -match 'AXIS_VERIFY_RESULT failures=(\d+) warnings=(\d+)') {
        $failures = [int]$matches[1]
        $warnings = [int]$matches[2]
    }
}

# --- T17 Observance ---
$memRoot = Join-Path $Root "Memory"
$t17State = Join-Path $memRoot "state\t17_state.json"
$t17Seals = Join-Path $memRoot "ledger\segment_seals.jsonl"
$t17Errors = Join-Path $memRoot "ledger\ingest_errors.jsonl"

# 1. Offset OK
$t17_offset_ok = $false
$t17_offset_val = 0
$t17_epoch_val = $null
if (Test-Path $t17State) {
    try {
        $st = Get-Content $t17State -Raw | ConvertFrom-Json
        $t17_offset_val = $st.last_offset
        if ($st.epoch_id) { $t17_epoch_val = $st.epoch_id }
        if ($t17_offset_val -ge 0) { $t17_offset_ok = $true } 
    }
    catch {}
}

# 2. Segment Seal OK (Latest)
$t17_seal_ok = $false
$t17_last_seal_file = $null
if (Test-Path $t17Seals) {
    try {
        $lastSeal = Get-Content $t17Seals -Tail 1 | ConvertFrom-Json
        $segPath = Join-Path $memRoot "ledger\$($lastSeal.file)"
        if (Test-Path $segPath) {
            $actHash = (Get-FileHash -Path $segPath -Algorithm SHA256).Hash
            if ($actHash -eq $lastSeal.sha256) {
                $t17_seal_ok = $true
                $t17_last_seal_file = $lastSeal.file
            }
            else {
                Write-Warning "T17 Seal Mismatch: $($lastSeal.file)"
            }
        }
    }
    catch {}
}

# 3. Errors Last 5m
$t17_recent_errors = 0
if (Test-Path $t17Errors) {
    try {
        $cutoff = (Get-Date).AddMinutes(-5).ToUniversalTime()
        $errs = Get-Content $t17Errors -Tail 50 
        foreach ($line in $errs) {
            $e = $line | ConvertFrom-Json
            if ([DateTime]::Parse($e.ts_utc) -gt $cutoff) { $t17_recent_errors++ }
        }
    }
    catch {}
}

# 4. Policy Integrity (Phase 24)
$policy_ok = $false
$policy_epoch = 0
$policy_hash = "UNKNOWN"
$verifierPolicy = Join-Path $Root "Governance\Axis_Verify_PolicyChain.ps1"

if (Test-Path $verifierPolicy) {
    try {
        $ledgerV2 = Join-Path $Root "Governance\policy_update_ledger_v2.jsonl"
        if (Test-Path $ledgerV2) {
            $pOut = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verifierPolicy -LedgerPath $ledgerV2 -VerifyRuntime:$false 2>&1
        }
        else {
            $pOut = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verifierPolicy 2>&1
        }
        if ($LASTEXITCODE -eq 0) {
            $policy_ok = $true
            # Parse output for details
            foreach ($line in $pOut) {
                if ($line -match 'Chain Verified \((\d+) blocks\)') { $policy_epoch = [int]$matches[1] }
                if ($line -match 'Head Hash: (.+)') { $policy_hash = $matches[1] }
            }
        }
    }
    catch {
        Write-Warning "Policy Verifier Exception: $_"
    }

    # --- Phase 27: Promoter Metrics ---
    $RuntimeDir = Join-Path $Root "Runtime\Decision" # Define RuntimeDir for new paths
    $promoterStatePath = Join-Path $RuntimeDir "promoter_state.json"
    $promotionLedgerPath = Join-Path $RuntimeDir "promoted_queue.jsonl"
    $intentQueuePath = Join-Path $RuntimeDir "intent_queue.jsonl"
    
    # Defaults
    $promoterState = @{ 
        counts        = @{ promoted_count = 0; lines_seen = 0 }
        ts_utc        = $null
        run_id        = "UNKNOWN"
        build         = "UNKNOWN"
        pending_range = @{ oldest_ts_utc = $null; newest_ts_utc = $null }
        cursor_file   = $null
    }

    if (Test-Path $promoterStatePath) {
        try { 
            $raw = Get-Content $promoterStatePath -Raw | ConvertFrom-Json
            if ($raw) { $promoterState = $raw }
        }
        catch {}
    }

    # Calculate Unconsumed Depth (Pending Work)
    # Promoter Depth: intent_queue_lines - promoter_cursor.line
    $promoter_cursor_line = 0
    if ($promoterState.cursor_file -and (Test-Path $promoterState.cursor_file)) {
        try { $promoter_cursor_line = (Get-Content $promoterState.cursor_file -Raw | ConvertFrom-Json).line } catch {}
    }
    
    $queueTotal = 0
    if (Test-Path $intentQueuePath) {
        $queueTotal = (Get-Content $intentQueuePath | Measure-Object).Count
    }
    $promoterDepth = [math]::Max(0, ($queueTotal - $promoter_cursor_line))

    # Executor Depth: promoted_queue_lines - executor_cursor.line
    $executor_cursor_line = 0
    $execCursorFile = Join-Path $RuntimeDir "executor_intent_queue_cursor.json"
    if (Test-Path $execCursorFile) {
        try { $executor_cursor_line = (Get-Content $execCursorFile -Raw | ConvertFrom-Json).line } catch {}
    }

    $promotedTotal = 0
    if (Test-Path $promotionLedgerPath) {
        $promotedTotal = (Get-Content $promotionLedgerPath | Measure-Object).Count
    }
    $executorDepth = [math]::Max(0, ($promotedTotal - $executor_cursor_line))
}

# --- Phase 39: Economic Forensics Monitoring ---
$spend_ok = $false
$spend_head_hash = "UNKNOWN"
$spend_count = 0
$verifierSpend = Join-Path $Root "Governance\Axis_Verify_EconomicForensics.ps1"
if (Test-Path $verifierSpend) {
    try {
        $sOut = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $verifierSpend 2>&1
        if ($LASTEXITCODE -eq 0) {
            $spend_ok = $true
            foreach ($line in $sOut) {
                if ($line -match 'Verified \((\d+) events\)') { $spend_count = [int]$matches[1] }
            }
            # Get last hash from file since verifier doesn't emit it yet in a matchable format
            if (Test-Path (Join-Path $Root "Truth_Engine\spend_ledger.jsonl")) {
                $spend_head_hash = (Get-Content (Join-Path $Root "Truth_Engine\spend_ledger.jsonl") -Tail 1 | ConvertFrom-Json).hash
            }
        }
    }
    catch {}
}

$entry = [ordered]@{
    schema                      = "axis.drift.heartbeat.v1"
    ts                          = $ts
    strict                      = $true
    exit_code                   = $exitCode
    failures                    = $failures
    warnings                    = $warnings
    capsule_sha256              = (Sha256Tag $capsule)
    verifier_path               = $verifier
    t17_offset_ok               = $t17_offset_ok
    t17_offset                  = $t17_offset_val
    t17_epoch                   = $t17_epoch_val
    t17_seal_ok                 = $t17_seal_ok
    t17_seal_file               = $t17_last_seal_file
    t17_recent_errors           = $t17_recent_errors
    policy_integrity            = $policy_ok
    policy_epoch                = $policy_epoch
    policy_hash                 = $policy_hash
    
    # Phase 27.1 Metrics
    promoter_pending            = $promoterDepth       # Unconsumed in intent_queue
    executor_pending            = $executorDepth       # Unconsumed in promoted_queue
    
    promoter_run_id             = $promoterState.run_id
    promoter_build              = $promoterState.build
    promoter_last_scan          = $promoterState.ts_utc
    promoter_promoted_last_scan = $promoterState.counts.promoted_count
    
    # Phase 37 Audit
    audit_integrity             = $audit_ok
    audit_head_hash             = $audit_head_hash
    audit_count                 = $audit_count

    # Phase 39 Economic Forensics
    spend_integrity             = $spend_ok
    spend_head_hash             = $spend_head_hash
    spend_count                 = $spend_count

    # Phase 38 Repair Tracking
    audit_repaired_since_boot   = (Test-Path (Join-Path $Root "Truth_Engine\audit_repair_ledger.jsonl"))

    t08_last_cycle_ts           = $t08_last_cycle_ts
}

# 5. Promoter Stats (Phase 27) - Legacy Block (Removed, merged above)

# Append heartbeat (UTF8 no BOM)
$line = ($entry | ConvertTo-Json -Compress)
[System.IO.File]::AppendAllText($LogPath, $line + "`n", (New-Object System.Text.UTF8Encoding($false)))

if ($exitCode -eq 0) {
    Write-Host "[PASS] Drift heartbeat OK" -ForegroundColor Green
}
else {
    Write-Host ("[FAIL] Drift heartbeat FAIL exit_code={0}" -f $exitCode) -ForegroundColor Red
    Write-Host "--- Verification Output ---"
    $out | ForEach-Object { Write-Host $_ }
    Write-Host "---------------------------"
}
exit $exitCode
