# Verify-LiveRotation.ps1
$ErrorActionPreference = "Stop"

$ErrorActionPreference = "Continue" # Changed from Stop to see errors

Write-Host "Importing Modules..."
Import-Module "D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1" -Force -Verbose
if (Get-Command Get-AxisSecret -ErrorAction SilentlyContinue) { 
    Write-Host "T09 Loaded OK." -ForegroundColor Green 
}
else { 
    Write-Host "T09 Failed to Load." -ForegroundColor Red; exit 1 
}

Import-Module "D:\Infinite\Infinity\Truth_Engine\T08_LifecycleGate.psm1" -Force

function Sign-V2Envelope {
    param($Identity, $KeyId, $Secret, $Nonce)
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

Write-Host ">>> Verifying V3 Cutover" -ForegroundColor Cyan

# 1. Create Envelopes
$v3Secret = "SuperSecretKEY123!" # Staged earlier
$v2Secret = Get-AxisSecret -KeyRef "dpapi:system_tester:v2" # Should still exist

$env3 = Sign-V2Envelope -Identity "system:tester" -KeyId "k_system_tester_v3" -Secret $v3Secret -Nonce "verify_v3"
$env2 = Sign-V2Envelope -Identity "system:tester" -KeyId "k_system_tester_v2" -Secret $v2Secret -Nonce "verify_v2"

# 2. Check Gate
Write-Host "Checking V3 (Should Pass)..."
$g3 = Test-AxisKeyLifecycleAllowed -Envelope $env3 -NoCache
if ($g3.ok) { Write-Host "PASS: V3 Allowed" -ForegroundColor Green }
else { Write-Host "FAIL: V3 Blocked ($($g3.reason))" -ForegroundColor Red }

Write-Host "Checking V2 (Should Fail Mismatch)..."
$g2 = Test-AxisKeyLifecycleAllowed -Envelope $env2 -NoCache
if (-not $g2.ok -and $g2.reason -eq "BLOCKED_KEY_MISMATCH") { Write-Host "PASS: V2 Blocked (Mismatch)" -ForegroundColor Green }
else { Write-Host "FAIL: V2 Unexpected ($($g2.ok) / $($g2.reason))" -ForegroundColor Red }
