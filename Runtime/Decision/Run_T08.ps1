# --- CONFIG & RUNTIME BOOTSTRAP (Phase 636) ---
$RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$Executor = Join-Path $RuntimeDir "T08_Executor.ps1"
$DecLog = Join-Path $RuntimeDir "decision_log.jsonl"
$CoinLedger = Join-Path $RuntimeDir "coin_ledger.jsonl"

# Ensure RuntimeDir exists
if (-not (Test-Path $RuntimeDir)) {
    New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null
}

# Ensure ledger exists (MUST RUN BEFORE ANY ABORT PATH)
if (-not (Test-Path $CoinLedger)) {
    # Create empty file deterministically (UTF8 No BOM is preferred for machine logs)
    "" | Set-Content -Path $CoinLedger -Encoding utf8
    Write-Host "[COIN] Initialized canonical ledger: $CoinLedger" -ForegroundColor Gray
    
    $bootEvt = [ordered]@{
        ts       = (Get-Date).ToUniversalTime().ToString("o")
        decision = "COIN_EVENT"
        event    = "LEDGER_INITIALIZED"
        path     = $CoinLedger
    }
    try { $bootEvt | ConvertTo-Json -Compress | Add-Content -Path $DecLog -Encoding utf8 } catch {}
}

# --- AUTHORITY PREFLIGHT: Hash Verification (Phase 635/636) ---
$CapsulePath = "D:\Infinite\Infinity\Governance\Sovereign_State_Capsule.json"
if (Test-Path $CapsulePath) {
    try {
        $capsule = Get-Content $CapsulePath -Raw | ConvertFrom-Json
        $hashes = $capsule.verification.authority_hashes
        $paths = $capsule.canonical_paths
        
        $failed = @()
        
        # Verify Executor
        if (Test-Path $paths.executor) {
            $h = Get-FileHash -Path $paths.executor -Algorithm SHA256
            if ("sha256:$($h.Hash)" -ne $hashes.executor_sha256) { $failed += "executor" }
        }
        else { $failed += "executor_missing" }

        # Verify Self (Wrapper)
        if (Test-Path $paths.run_t08) {
            $h = Get-FileHash -Path $paths.run_t08 -Algorithm SHA256
            if ("sha256:$($h.Hash)" -ne $hashes.run_t08_sha256) { $failed += "run_t08" }
        }
        else { $failed += "run_t08_missing" }

        # Verify System Mode
        if (Test-Path $paths.system_mode) {
            $h = Get-FileHash -Path $paths.system_mode -Algorithm SHA256
            if ("sha256:$($h.Hash)" -ne $hashes.system_mode_sha256) { $failed += "system_mode" }
        }
        else { $failed += "system_mode_missing" }


        if (Test-Path $paths.constraints) {
            $h = Get-FileHash -Path $paths.constraints -Algorithm SHA256
            if ("sha256:$($h.Hash)" -ne $hashes.constraints_sha256) { $failed += "constraints" }
        }
        else { $failed += "constraints_missing" }

        # Verify Contract
        if (Test-Path $paths.contract) {
            $h = Get-FileHash -Path $paths.contract -Algorithm SHA256
            if ("sha256:$($h.Hash)" -ne $hashes.contract_sha256) { $failed += "contract" }
        }
        else { $failed += "contract_missing" }

        if ($failed.Count -gt 0) {
            $msg = "[AUTHORITY BLOCK] Hash Mismatch detected in canonical authority files: $($failed -join ', ')"
            Write-Error $msg
            $failEvent = [ordered]@{
                ts                = (Get-Date).ToUniversalTime().ToString("o")
                event             = "AUTHORITY_HASH_MISMATCH"
                failed_components = $failed
            }
            $failEvent | ConvertTo-Json -Compress | Add-Content $DecLog -Encoding UTF8
            exit 1 # ABORT EXECUTION (Phase 636 Law)
        }
        Write-Host "[AUTHORITY] Preflight Hash Verification: PASSED." -ForegroundColor Green
    }
    catch {
        $msg = "[AUTHORITY FATAL] Preflight validation failed: $($_.Exception.Message)"
        Write-Error $msg
        # Final safety exit
        exit 1
    }
}

# --- AUTHORITY AUDIT: Duplicate Contracts (Phase 634) ---
$canonicalContract = "D:\Infinite\Infinity\Autonomy_Contract.json"
try {
    $allContracts = Get-ChildItem -Path "D:\Infinite" -Filter "Autonomy_Contract.json" -Recurse -ErrorAction SilentlyContinue | Select-Object -ExpandProperty FullName
    $excludePaths = "Temp_", "Backups", "Lab", "Tests", "Snapshots"
    $duplicates = $allContracts | Where-Object { 
        $path = $_
        $isCanonical = ($path -eq $canonicalContract)
        $isExcluded = $excludePaths | Where-Object { $path -like "*$_*" }
        (-not $isCanonical) -and (-not $isExcluded)
    }
    if ($duplicates) {
        Write-Warning "[AUTHORITY ALERT] Duplicate Autonomy_Contract.json instances detected outside canonical path!"
        foreach ($dup in $duplicates) { Write-Warning "  -> Duplicate: $dup" }
    }
}
catch {}

$WrapperBuild = if ($PSCommandPath) {
    (Get-Item $PSCommandPath).LastWriteTimeUtc.ToString("yyyyMMdd-HHmmss")
}
else {
    "Unknown"
}

# --- Telemetry Context (for Executor) ---
$env:AXIS_WRAPPER = "Run_T08"
$env:AXIS_WRAPPER_BUILD = $WrapperBuild

# --- Reflex: Compile Policy Snapshot (Nervous System Refresh) ---
try {
    if (-not (Get-Command Compile-PolicySnapshot -ErrorAction SilentlyContinue)) {
        Import-Module "D:\Infinite\Infinity\Truth_Engine\T05_PolicyCompiler.psm1" -Force -DisableNameChecking -ErrorAction SilentlyContinue
    }
    # We update the snapshot on every wrapper launch to ensure T08 execution sees fresh immune state
    Write-PolicySnapshot | Out-Null
}
catch {}

$NowUtc = (Get-Date).ToUniversalTime().ToString("o")

# --- Capture Provenance Envelope ---
$Envelope = [ordered]@{
    ts              = $NowUtc
    decision        = "WRAPPER_LAUNCH"
    wrapper_build   = $WrapperBuild
    wrapper_pid     = $PID
    wrapper_host    = $env:COMPUTERNAME
    executor_path   = $Executor
    executor_exists = Test-Path $Executor
    caller_script   = $MyInvocation.ScriptName
}

# --- Detailed Caller Identification (Forensics) ---
try {
    $p = Get-CimInstance Win32_Process -Filter "ProcessId=$PID"
    $pp = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $p.ParentProcessId)

    $Envelope.parent_pid = $p.ParentProcessId
    $Envelope.parent_cmd = $pp.CommandLine
    $Envelope.self_cmd = $p.CommandLine

    # Track Grandparent (Scheduler -> Launcher -> Wrapper chains)
    if ($pp.ParentProcessId) {
        try {
            $gpp = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $pp.ParentProcessId)
            $Envelope.gparent_pid = $pp.ParentProcessId
            $Envelope.gparent_cmd = $gpp.CommandLine
        }
        catch {}
    }

    # Detect EncodedCommand (Dual Decoder: UTF-16LE vs UTF-8)
    if ($Envelope.parent_cmd -match '-EncodedCommand\s+([A-Za-z0-9+/=]+)') {
        try {
            $b64 = $Matches[1]
            $bytes = [Convert]::FromBase64String($b64)

            # Default: PowerShell EncodedCommand is UTF-16LE
            $decoded16 = [Text.Encoding]::Unicode.GetString($bytes)
            
            # Fallback: some wrappers encode UTF8
            $decoded8 = [Text.Encoding]::UTF8.GetString($bytes)

            $Envelope.parent_decoded_utf16 = $decoded16
            if ($decoded8 -and $decoded8 -ne $decoded16) {
                $Envelope.parent_decoded_utf8 = $decoded8
            }
        }
        catch {}
    }

    # Call Stack (Stringified for JSON safety)
    $cs = Get-PSCallStack
    $Envelope.callstack_top = @($cs | Select-Object -First 6 | ForEach-Object { "$($_.Command) @ $($_.Location)" })

    if (Get-Command Calculate-Fingerprint -ErrorAction SilentlyContinue) {
        $printRaw = ($Envelope.parent_cmd + "|" + $Envelope.gparent_cmd + "|" + $Envelope.parent_decoded_utf16)
        $print = Calculate-Fingerprint -str $printRaw
        $Envelope.fingerprint = $print
    }

}
catch {}

# --- Optional Drift Signals (Non Blocking) ---
$DriftFlags = @()

if (-not (Test-Path $Executor)) {
    $DriftFlags += "EXECUTOR_MISSING"
}

# Detect if executor changed in last minute (hot patch detection)
try {
    if (Test-Path $Executor) {
        $lastWrite = (Get-Item $Executor).LastWriteTimeUtc
        if (([DateTime]::UtcNow - $lastWrite).TotalSeconds -lt 60) {
            $DriftFlags += "EXECUTOR_RECENTLY_MODIFIED"
        }
    }
}
catch {}

if ($DriftFlags.Count -gt 0) {
    $Envelope.drift_flags = $DriftFlags
}

# --- Log Envelope ---
try {
    $Envelope | ConvertTo-Json -Compress | Add-Content $DecLog -Encoding utf8
}
catch {}

# --- Execution ---
if (Test-Path $Executor) {

    try {
        & $Executor @args
    }
    catch {
        $err = [ordered]@{
            ts            = (Get-Date).ToUniversalTime().ToString("o")
            decision      = "WRAPPER_EXEC_EXCEPTION"
            wrapper_pid   = $PID
            executor_path = $Executor
            error         = $_.Exception.Message
        }

        try { $err | ConvertTo-Json -Compress | Add-Content $DecLog -Encoding UTF8 } catch {}
        throw
    }

}
else {

    $fail = [ordered]@{
        ts       = (Get-Date).ToUniversalTime().ToString("o")
        decision = "WRAPPER_BLOCK"
        reason   = "EXECUTOR_NOT_FOUND"
        path     = $Executor
    }

    try { $fail | ConvertTo-Json -Compress | Add-Content $DecLog -Encoding UTF8 } catch {}

    Write-Error "T08_Executor.ps1 not found at $Executor"
}

# --- Post-Execution Analytics ---
if (Get-Command Measure-ExecutionAnalytics -ErrorAction SilentlyContinue) {
    Measure-ExecutionAnalytics | Out-Null
}

# --- Post-Execution Calibration (Phase 14) ---
if (Get-Command Measure-CalibrationState -ErrorAction SilentlyContinue) {
    Measure-CalibrationState | Out-Null
}

$calibModeFile = "D:\Infinite\Infinity\Runtime\Decision\calibration_mode.json"
if (Test-Path $calibModeFile) {
    $cm = Get-Content $calibModeFile -Raw | ConvertFrom-Json
    if ($cm.mode -eq "propose") {
        if (Get-Command Propose-CalibrationAdjustments -ErrorAction SilentlyContinue) {
            Propose-CalibrationAdjustments | Out-Null
        }
    }
}


# --- Phase 16: Feedback Loops (Pulse) ---
if (Get-Command Get-FeedbackRollup -ErrorAction SilentlyContinue) { Get-FeedbackRollup | Out-Null } elseif (Test-Path 'D:\Infinite\Infinity\Truth_Engine\T16_FeedbackRollup.psm1') { Import-Module 'D:\Infinite\Infinity\Truth_Engine\T16_FeedbackRollup.psm1' -Force -DisableNameChecking; Get-FeedbackRollup | Out-Null }

# --- Phase 17: Memory Ledger (Pulse) ---
if (Get-Command Update-MemoryLedger -ErrorAction SilentlyContinue) { Update-MemoryLedger | Out-Null } elseif (Test-Path 'D:\Infinite\Infinity\Truth_Engine\T17_MemoryIndexer.psm1') { Import-Module 'D:\Infinite\Infinity\Truth_Engine\T17_MemoryIndexer.psm1' -Force -DisableNameChecking; Update-MemoryLedger | Out-Null }
