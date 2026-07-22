# Axis_Runtime_Integrity_Watchdog.ps1
# Linear Skeleton

param(
    [string]$Mode = "FAST"
)

$ErrorActionPreference = "Stop"
$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$PulseLedger = Join-Path $GovDir "integrity_pulse_ledger.jsonl"

Write-Host "--- WATCHDOG LINEAR ---" -ForegroundColor Cyan

$EconModule = Join-Path $GovDir "Economics\Axis_IntegrityEconomics.psm1"
if (Test-Path $EconModule) { Import-Module $EconModule -Force }

# 1. Dummy Component -> Real Components
$componentResults = New-Object System.Collections.Generic.List[Object]

# Define Check Components
$checks = @()
$checks += @{ name = "ForensicJoins"; script = Join-Path $GovDir "Axis_Verify_ForensicJoins.ps1" }
$checks += @{ name = "RotationContinuity"; script = Join-Path $GovDir "Axis_Log_Rotation.ps1"; args = @("-VerifyOnly") }

if ($Mode -eq "DEEP") {
    $checks += @{ name = "HistoricalReplay"; script = Join-Path $GovDir "Axis_Verify_Replay.ps1" }
    $checks += @{ name = "WarmStorageIntegrity"; script = Join-Path $GovDir "Axis_Verify_WarmStorage.ps1" }
    $checks += @{ name = "TemporalChain"; script = Join-Path $TruthDir "Axis_Verify_TemporalChain.ps1" }
    $checks += @{ name = "PolicyChain"; script = Join-Path $GovDir "Axis_Verify_PolicyChain.ps1" }
    $checks += @{ name = "ExternalAnchors"; script = Join-Path $GovDir "Axis_Verify_ExternalAnchors.ps1" }
}

foreach ($c in $checks) {
    $cStartTime = Get-Date
    Write-Host "Running $($c.name)..." -NoNewline
    
    $status = "SUCCESS"
    $exitCode = 0
    try {
        if ($c.args) {
            $scriptPath = $c.script
            $argsList = @($c.args)
            powershell -NoProfile -ExecutionPolicy Bypass -File $scriptPath @argsList
        }
        else {
            powershell -NoProfile -ExecutionPolicy Bypass -File $c.script
        }
        if ($LASTEXITCODE -ne 0) {
            $status = "FAIL"
            $exitCode = $LASTEXITCODE
        }
    }
    catch {
        $status = "FAIL"
        Write-Host "DEBUG: $($_.Exception.Message)" -ForegroundColor Yellow
        $exitCode = 1
    }
    if ($status -eq "FAIL") { Write-Host " [FAIL]" -ForegroundColor Red }
    if ($status -eq "SUCCESS") { Write-Host " [OK]" -ForegroundColor Green }

    $dur = ((Get-Date) - $cStartTime).TotalMilliseconds
    $ms = [int][Math]::Round($dur)

    $compResult = [ordered]@{
        "name"      = [string]$c.name
        "status"    = [string]$status
        "exit_code" = [int]$exitCode
        "ms"        = $ms
    }
    $componentResults.Add($compResult)

    if (Get-Command Write-EconEvent -ErrorAction SilentlyContinue) {
        Write-EconEvent -Component $c.name -Action $c.name -Mode $Mode -DurationMs $ms -NoRebuild
    }
}

# 6. State Vector & Drift Check
$vectorScript = Join-Path $GovDir "Get-AxisStateVector.ps1"
$stateVector = $null
$driftDetected = $false
$driftReason = $null # Explicitly initialized
    
if (Test-Path $vectorScript) {
    try {
        # Execute script
        $rawVector = & $vectorScript
            
        # Unwrap if array (PowerShell pipeline quirk)
        if ($rawVector -is [Array]) {
            $rawObj = $rawVector | Select-Object -Last 1
        }
        else {
            $rawObj = $rawVector
        }
            
        if ($rawObj) {
            # Sanitize to ordered dictionary
            $stateVector = [ordered]@{
                "ts_utc"            = [string]$rawObj.ts_utc
                "witness_tip"       = [string]$rawObj.witness_tip
                "anchor_tip"        = [string]$rawObj.anchor_tip
                "pulse_tip"         = [string]$rawObj.pulse_tip
                "econ_tip"          = [string]$rawObj.econ_tip
                "hot_segment_count" = [int]$rawObj.hot_segment_count
                "warm_pack_count"   = [int]$rawObj.warm_pack_count
                "genesis_reachable" = [bool]$rawObj.genesis_reachable
            }
                
            # DRIFT CHECK IMPLEMENTATION (Phase 62 Policy Aware)
            # Compare Witness (Canonical) vs Live (Runtime)
                
            # 1. Load Policy and Canonical Paths
            $policyFile = Join-Path $GovDir "integrity_policy.json"
            $witnessMode = "SOFT" # Default Safety
            $driftWitnessFile = Join-Path $GovDir "Axis_Witness_Ledger.jsonl" # Default
                
            if (Test-Path $policyFile) {
                try {
                    $pol = Get-Content $policyFile -Raw | ConvertFrom-Json
                    if ($pol.witness_mode) { $witnessMode = $pol.witness_mode }
                    if ($pol.paths.witness_ledger) { $driftWitnessFile = $pol.paths.witness_ledger }
                }
                catch { Write-Host "Policy Config Error: $_" -ForegroundColor Yellow }
            }

            if ($witnessMode -ne "OFF") {
                if (Test-Path $driftWitnessFile) { 
                    # Relaxed Regex for Schema Variance (type/kind/event)
                    $witnessCount = (Select-String -Path $driftWitnessFile -Pattern '"(type|kind|event)":\s*"segment_created"').Count
                    $liveCount = [int]$stateVector.hot_segment_count
                    if ($witnessCount -ne $liveCount) {
                        $driftDetected = $true
                        $msg = "SegmentMismatch: Witness=$witnessCount, Live=$liveCount"
                        $driftReason = $msg
                            
                        if ($witnessMode -eq "STRICT") {
                            Write-Host "DRIFT DETECTED (STRICT): $msg" -ForegroundColor Red
                        }
                        else {
                            # SOFT Mode: Record drift but warn only
                            Write-Host "Integrity Warning (SOFT - DRIFT PRESENT): $msg" -ForegroundColor Yellow
                            $driftReason = "WARNING (SOFT): $msg"
                        }
                    }
                }
                else {
                    # Fact: Witness missing
                    $driftDetected = $true
                    $msg = "WitnessMissing: $driftWitnessFile"
                    $driftReason = $msg
                        
                    if ($witnessMode -eq "SOFT") {
                        Write-Host "Integrity Warning (SOFT): Witness File Missing" -ForegroundColor Yellow
                        $driftReason = "WARNING (SOFT): $msg"
                    }
                    else {
                        Write-Host "DRIFT DETECTED (STRICT): Witness File Missing" -ForegroundColor Red
                    }
                }

                # CRITICAL: Always write Pulse to Ledger using UTF-8 (singleton fact record)
                $PulseLine = $pulse | ConvertTo-Json -Compress
                Add-Content -Path $driftPulseFile -Value $PulseLine -Encoding utf8
            }
        }
    }
    catch {
        Write-Host "WARNING: State Vector Failed: $_" -ForegroundColor Yellow
        $stateVector = $null
    }
}

# 3. Pulse Record
$overallStatus = "SUCCESS"
$exitCode = 0
foreach ($res in $componentResults) {
    if ($res.status -ne "SUCCESS") {
        $overallStatus = "FAIL"
        $exitCode = 1
    }
}

$pulse = [ordered]@{
    pulse_id       = [Guid]::NewGuid().ToString()
    ts_utc         = (Get-Date).ToUniversalTime().ToString("o")
    mode           = $Mode
    status         = $overallStatus
    exit_code      = $exitCode
    components     = $componentResults
    state_vector   = $stateVector
    drift_detected = [bool]$driftDetected
    drift_reason   = $driftReason
}

$json = $pulse | ConvertTo-Json -Depth 10 -Compress

# Checksum
$sha = [System.Security.Cryptography.SHA256]::Create()
$bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
$hash = [BitConverter]::ToString($sha.ComputeHash($bytes)) -replace "-", ""
$sha.Dispose()
$pulse["hash"] = "sha256:" + $hash.ToLower()

$finalJson = $pulse | ConvertTo-Json -Depth 10 -Compress
Add-Content -Path $PulseLedger -Value $finalJson

Write-Host "Recorded Pulse: $($pulse.hash)" -ForegroundColor Green
