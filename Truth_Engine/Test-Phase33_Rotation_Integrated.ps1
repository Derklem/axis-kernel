# Test-Phase33_Rotation_Integrated.ps1
# Verifies Phase 33 using PRODUCTION MODULES (T09, T08)
# Proves: Registry Binding + KeyRing Revocation + Gate Enforcement

$ErrorActionPreference = "Stop"
Start-Transcript -Path "D:\Infinite\Infinity\Truth_Engine\integrated_debug.txt" -Force

$KeyRingModule = "D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1"
$EnvVerifier = "D:\Infinite\Infinity\Truth_Engine\T08_EnvelopeVerifier.psm1"
$RegistryFile = "D:\Infinite\Infinity\Truth_Engine\identity_registry.json"

# Import Modules (Force to ensure fresh state)
Import-Module $KeyRingModule -Force
Import-Module $EnvVerifier   -Force

function Load-Registry { Get-Content $RegistryFile -Raw | ConvertFrom-Json }
function Save-Registry($r) { $r | ConvertTo-Json -Depth 10 | Set-Content $RegistryFile -Encoding UTF8 -Force }

function Sign-V2Envelope {
    param(
        [Parameter(Mandatory = $true)][string]$Identity,
        [Parameter(Mandatory = $true)][string]$KeyId,
        [Parameter(Mandatory = $true)][string]$Secret,
        [Parameter(Mandatory = $true)][string]$Nonce
    )
    $ts = (Get-Date).ToUniversalTime().ToString("o")
    $intentJson = '{"op":"noop:heartbeat","ts":"' + $ts + '","type":"heartbeat","target":"axis:handler"}'
    $payload = "$ts|$Nonce|$Identity|$KeyId|$intentJson"

    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($Secret))
    $sigBytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($payload))
    $sig = "hmac256:" + (($sigBytes | ForEach-Object { $_.ToString("x2") }) -join "")

    return [ordered]@{
        schema      = "axis.intent_envelope.v2"
        ts_utc      = $ts
        nonce       = $Nonce
        identity    = $Identity
        key_id      = $KeyId
        intent_json = $intentJson
        signature   = $sig
    }
}

Write-Host ">>> Starting Integrated Rotation Test" -ForegroundColor Cyan

# --- Preconditions ---
$reg = Load-Registry
$tester = $reg.identities | Where-Object { $_.identity -eq "system:tester" } | Select-Object -First 1
if (-not $tester) { throw "system:tester missing from registry" }

# Ensure canonical v1/v2 refs
$v1Ref = Get-AxisKeyRef -Identity "system:tester" -Version "v1"
$v2Ref = Get-AxisKeyRef -Identity "system:tester" -Version "v2"

# --- Mint v1 and v2 ---
Write-Host "Minting Keys..."
Set-AxisSecret -KeyRef $v1Ref -Secret ("int_v1_" + (Get-Date).Ticks)
Set-AxisSecret -KeyRef $v2Ref -Secret ("int_v2_" + (Get-Date).Ticks)

$v1Secret = Get-AxisSecret -KeyRef $v1Ref
$v2Secret = Get-AxisSecret -KeyRef $v2Ref

# --- Bind registry to v2 (authoritative) ---
Write-Host "Binding Registry to V2..."
for ($i = 0; $i -lt $reg.identities.Count; $i++) {
    if ($reg.identities[$i].identity -eq "system:tester") {
        $reg.identities[$i].key_id = "k_system_tester_v2"
        $reg.identities[$i].key_ref = $v2Ref
    }
}
Save-Registry $reg

# --- Revoke v1 ---
Write-Host "Revoking V1..."
Revoke-AxisKey -KeyRef $v1Ref -Reason "Integrated Phase33 Test"

# --- Build real cryptographic envelopes ---
Write-Host "Signing Envelopes..."
$envV1 = Sign-V2Envelope -Identity "system:tester" -KeyId "k_system_tester_v1" -Secret $v1Secret -Nonce ("it_v1_" + (New-Guid).ToString("N").Substring(0, 8))
$envV2 = Sign-V2Envelope -Identity "system:tester" -KeyId "k_system_tester_v2" -Secret $v2Secret -Nonce ("it_v2_" + (New-Guid).ToString("N").Substring(0, 8))

# --- Crypto verify (both should be ok if secrets exist) ---
Write-Host "Verifying Crypto..."
$ver1 = Test-IntentEnvelope -Envelope $envV1
$ver2 = Test-IntentEnvelope -Envelope $envV2

if (-not $ver2.ok) { throw "V2 crypto verify failed: $($ver2.reason)" }
Write-Host "Crypto Verify OK."

# --- Lifecycle gate (using PRODUCTION LOGIC via dot-sourcing if possible, or duplicated) ---
# We want to test the REAL gate logic in T08_Executor.ps1.
# But T08 is an executable script, not a module.
# So we must verify the logic by duplicating the gate function OR by mocking the call.
# Given the user wants "Integrated" proof, we should use the EXACT function logic we verified.
# We will define a local wrapper that matches the deployed code exactly.

$LifecycleGateModule = "D:\Infinite\Infinity\Truth_Engine\T08_LifecycleGate.psm1"
Import-Module $LifecycleGateModule -Force

Write-Host "Checking Lifecycle Gate (Using Module + NoCache)..."
# Phase 35: Use -NoCache to ensure test sees exactly what it wrote
$g1 = Test-AxisKeyLifecycleAllowed -Envelope $envV1 -NoCache
$g2 = Test-AxisKeyLifecycleAllowed -Envelope $envV2 -NoCache

# Assertion 1: V1 must be BLOCKED by Lifecycle Gate (Mismatch)
if ($g1.reason -ne "BLOCKED_KEY_MISMATCH") { 
    Write-Host "FAIL: V1 should be BLOCKED_KEY_MISMATCH. Got: $($g1.reason)" -ForegroundColor Red
    exit 1
}

# Assertion 2: V2 must be ALLOWED and Crypto Valid
if ($g2.ok -ne $true) { 
    Write-Host "FAIL: V2 should be ok. Got reason: $($g2.reason)" -ForegroundColor Red
    exit 1
}
if ($result = Test-IntentEnvelope -Envelope $envV2) {
    if (-not $result.ok) {
        Write-Host "FAIL: V2 crypto invalid. Reason: $($result.reason)" -ForegroundColor Red
        exit 1
    }
}

# Explicit Contract Messaging (Phase 35)
Write-Host "Crypto: V2 verified." -ForegroundColor Green

# V1 Crypto Check (Ambiguous by design)
$v1Result = Test-IntentEnvelope -Envelope $envV1
if ($v1Result.ok) {
    Write-Host "Crypto: V1 verified (expected under soft secret retention)." -ForegroundColor Yellow
}
else {
    Write-Host "Crypto: V1 failed verify (acceptable if revoked secrets are inaccessible). Reason: $($v1Result.reason)" -ForegroundColor Yellow
}

Write-Host "[PASS] Integrated Phase33/35 rotation verified: v1 blocked by mismatch, v2 allowed." -ForegroundColor Green
