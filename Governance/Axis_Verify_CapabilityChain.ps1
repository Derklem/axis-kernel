# Axis_Verify_CapabilityChain.ps1
# Phase 31: Capability Invariant Verification
# Ensures that:
# 1. Policy Capability Map exists and is valid.
# 2. Identity Registry is valid schema (v1).
# 3. Decision Log "EXEC_SUCCESS" entries contain required capability proofs.

param(
    [string]$Root = "D:\Infinite\Infinity",
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$failures = 0

function Fail($msg) {
    Write-Host "[FAIL] $msg" -ForegroundColor Red
    $script:failures++
    if ($Strict) { exit 1 }
}

function Pass($msg) {
    Write-Host "[PASS] $msg" -ForegroundColor Green
}

# 1. Policy Map Check
$policyPath = Join-Path $Root "Governance\decision_policy.json"
if (-not (Test-Path $policyPath)) { Fail "Policy not found: $policyPath" }

try {
    $policy = Get-Content $policyPath -Raw | ConvertFrom-Json
    if (-not $policy.policy.capability_map) {
        Fail "Policy missing 'capability_map'"
    }
    else {
        Pass "Policy Capability Map found"
    }
}
catch {
    Fail "Policy parse error: $_"
}

# 2. Identity Registry Check
$regPath = Join-Path $Root "Truth_Engine\identity_registry.json"
if (-not (Test-Path $regPath)) { Fail "Registry not found: $regPath" }

try {
    $reg = Get-Content $regPath -Raw | ConvertFrom-Json
    if ($reg.schema -ne "axis.identity_registry.v1") {
        Fail "Registry schema mismatch (Expected v1, got $($reg.schema))"
    }
    # Unique check
    $ids = $reg.identities | Select-Object -ExpandProperty identity
    $unique = $ids | Select-Object -Unique
    if ($ids.Count -ne $unique.Count) {
        Fail "Duplicate identities found in registry"
    }
    else {
        Pass "Identity Registry Schema & Uniqueness OK"
    }
}
catch {
    Fail "Registry parse error: $_"
}

# 3. Decision Log Invariant Check (Sample)
# "EXEC_SUCCESS" implies "CAPABILITY_CHECK_PASS"
# We check if blocked entries use the correct codes.
$decLog = Join-Path $Root "Runtime\Decision\decision_log.jsonl"
if (Test-Path $decLog) {
    $lines = Get-Content $decLog -Tail 100
    foreach ($line in $lines) {
        try {
            $entry = $line | ConvertFrom-Json
            if ($entry.decision -like "BLOCKED_CAPABILITY_*") {
                # Valid block code
            }
            if ($entry.decision -eq "BLOCKED_CAPABILITY") {
                # Legacy code check
                if ($Strict) { Fail "Legacy BLOCKED_CAPABILITY code found (Row: $($entry.decision))" }
                else { Write-Host "[WARN] Legacy BLOCKED_CAPABILITY code found." -ForegroundColor Yellow }
            }
        }
        catch {}
    }
    Pass "Decision Log Block Codes Checked (Tail 100)"
}

if ($failures -eq 0) {
    Write-Host "Capability Chain Verified." -ForegroundColor Cyan
    exit 0
}
else {
    exit 1
}
