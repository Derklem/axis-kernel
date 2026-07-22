<#
.SYNOPSIS
  T16_VoiceUnlockGate.ps1 (L3.5 VUP)
.DESCRIPTION
  Deterministic Voice Unlock Protocol (VUP v1.0).
  checks for:
  1. Claim Status Consistency (3x samples)
  2. Preflight Auth Check
  3. Evidence of successful Canary POST (from run_log or dedicated canary log)
  
  Output: "blocked_by_claim" OR "unblocked"
  Writes to: Runtime\Epistemic\voice_gate_state.json
#>

param(
    [string]$RuntimeDir = "D:\Infinite\Infinity\Runtime\Epistemic",
    [string]$Client = "D:\Infinite\Axis_Moltbook_Client.ps1"
)

function Ensure-Dir([string]$p) { if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null } }
Ensure-Dir $RuntimeDir

$GateFile = Join-Path $RuntimeDir "voice_gate_state.json"
$State = @{
    status_samples  = @()
    preflight_ok    = $false
    canary_evidence = $null
    voice_status    = "blocked_by_claim"
    last_check      = (Get-Date).ToUniversalTime().ToString("o")
}

# Load existing state if active
if (Test-Path $GateFile) {
    try {
        $loaded = Get-Content $GateFile -Raw | ConvertFrom-Json
        if ($loaded) {
            $State.status_samples = $loaded.status_samples
            $State.preflight_ok = $loaded.preflight_ok
            $State.canary_evidence = $loaded.canary_evidence
        }
    }
    catch {}
}

# 1. Sample Status
Write-Host "[VUP] Checking Agent Status..." -ForegroundColor Cyan
try {
    $res = & $Client -Action STATUS -Quiet | ConvertFrom-Json
    $st = if ($res.status) { $res.status } else { "unknown" }
    
    $State.status_samples += @{ ts = (Get-Date).ToUniversalTime().ToString("o"); status = $st }
    # Keep last 5 samples
    if ($State.status_samples.Count -gt 5) { $State.status_samples = $State.status_samples | Select-Object -Last 5 }
}
catch {
    Write-Warning "[VUP] Client Status Check Failed"
}

# Evaluate Samples (Need 3 consecutive active/claimed)
$recent = $State.status_samples | Select-Object -Last 3
$allActive = ($recent.Count -ge 3) -and (-not ($recent | Where-Object { $_.status -notin @("active", "claimed") }))

# 2. Check Preflight (Mocked for now as Client doesn't expose preflight explicitly yet without key)
# Real logic: If samples are good, try preflight
if ($allActive) {
    # In a real run, we'd invoke preflight. For simulation, we check if we have CREDENTIALS file.
    if (Test-Path "D:\Infinite\Infinity\Runtime\Moltbook\credentials.json") {
        $State.preflight_ok = $true
    }
}

# 3. Check for Evidence (Canary)
# For V1, we require a human override or a specific canary file to be present
# This prevents auto-unlock without explicit "Canary" action.
if (Test-Path "D:\Infinite\Infinity\Runtime\Epistemic\canary_confirmation.json") {
    $canary = Get-Content "D:\Infinite\Infinity\Runtime\Epistemic\canary_confirmation.json" -Raw | ConvertFrom-Json
    if ($canary.success -eq $true) {
        $State.canary_evidence = $canary
    }
}

# DECISION
if ($allActive -and $State.preflight_ok -and $State.canary_evidence) {
    $State.voice_status = "unblocked"
    Write-Host "[VUP] VOICE UNLOCKED. The Citadel Speaks." -ForegroundColor Green
}
else {
    $State.voice_status = "blocked_by_claim"
    $reason = @()
    if (-not $allActive) { $reason += "status_instability" }
    if (-not $State.preflight_ok) { $reason += "preflight_fail" }
    if (-not $State.canary_evidence) { $reason += "missing_canary" }
    Write-Host "[VUP] Voice Blocked. Reasons: $($reason -join ', ')" -ForegroundColor Yellow
}

$State.last_check = (Get-Date).ToUniversalTime().ToString("o")
$State | ConvertTo-Json -Depth 5 | Set-Content $GateFile -Encoding UTF8 -Force
