# Test-Phase32_Infra.ps1
# Verifies Phase 32 Signature Infrastructure (Envelope v2 + KeyID Binding)

Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1
$Verifier = "D:\Infinite\Infinity\Truth_Engine\T08_EnvelopeVerifier.psm1"
Import-Module $Verifier -Force

function Sign-V2 {
    param($identity, $op, $nonce, $keyIdOverride = $null)
    
    $reg = Get-Content D:\Infinite\Infinity\Truth_Engine\identity_registry.json -Raw | ConvertFrom-Json
    $signer = $reg.identities | Where-Object { $_.identity -eq $identity } | Select-Object -First 1
    
    $kid = if ($keyIdOverride) { $keyIdOverride } else { $signer.key_id }
    $ts = (Get-Date).ToUniversalTime().ToString("o")
    $intentJson = '{"op":"' + $op + '","ts":"' + $ts + '"}'
    
    $payload = "$ts|$nonce|$identity|$kid|$intentJson"
    $secret = Get-AxisSecret -KeyRef $signer.key_ref
    
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($secret))
    $sigBytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($payload))
    $sig = "hmac256:" + (($sigBytes | ForEach-Object { $_.ToString("x2") }) -join "")
    
    return [ordered]@{
        schema      = "axis.intent_envelope.v2"
        ts_utc      = $ts
        nonce       = $nonce
        identity    = $identity
        key_id      = $kid
        intent_json = $intentJson
        signature   = $sig
    }
}

Write-Host ">>> Starting Phase 32 Infrastructure Verification" -ForegroundColor Cyan

# 1. Valid v2 Test
Write-Host "`nTest 1: Valid v2 Envelope"
$env1 = Sign-V2 -identity "system:tester" -op "test:v2" -nonce "v2_test_001"
$res1 = Test-IntentEnvelope -Envelope $env1
if ($res1.ok) { Write-Host "[PASS] Valid v2 Verified" -ForegroundColor Green } else { Write-Error "Test 1 Failed: $($res1.reason)" }

# 2. KeyID Mismatch Test (Identity Registry check)
Write-Host "`nTest 2: KeyID Mismatch (Reg vs Envelope)"
$env2 = Sign-V2 -identity "system:tester" -op "test:v2" -nonce "v2_test_002" -keyIdOverride "k_WRONG_KEY"
$res2 = Test-IntentEnvelope -Envelope $env2
if (-not $res2.ok -and $res2.reason -match "key_mismatch") { Write-Host "[PASS] Correctly blocked KeyID Mismatch" -ForegroundColor Green } else { Write-Error "Test 2 Failed: $($res2.reason)" }

# 3. Signature Tamper Test (KeyID tempered)
Write-Host "`nTest 3: Signature Tamper (Payload Tempered)"
$env3 = Sign-V2 -identity "system:tester" -op "test:v2" -nonce "v2_test_003"
$env3.key_id = "k_system_tester_v1" # Even if it's the "right" ID, if it wasn't the one used for the signature calculation in Sign-V2 (unlikely here but for demonstration)
# Let's change identity instead
$env3.identity = "system:harness"
$res3 = Test-IntentEnvelope -Envelope $env3
if (-not $res3.ok -and $res3.reason -eq "signature_mismatch") { Write-Host "[PASS] Correctly blocked Tampered Payload" -ForegroundColor Green } else { Write-Error "Test 3 Failed: $($res3.reason)" }

# 4. Backward Compatibility (v1)
Write-Host "`nTest 4: Backward Compatibility (v1 Support)"
$ts = (Get-Date).ToUniversalTime().ToString("o")
$payload = "$ts|v1_test_004|system:tester|{}"
$reg = Get-Content D:\Infinite\Infinity\Truth_Engine\identity_registry.json -Raw | ConvertFrom-Json
$signer = $reg.identities | Where-Object { $_.identity -eq "system:tester" } | Select-Object -First 1
$secret = Get-AxisSecret -KeyRef $signer.key_ref
$hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($secret))
$sig = "hmac256:" + (($hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($payload)) | ForEach-Object { $_.ToString("x2") }) -join "")

$env4 = [ordered]@{
    schema      = "axis.intent_envelope.v1"
    ts_utc      = $ts
    nonce       = "v1_test_004"
    identity    = "system:tester"
    intent_json = "{}"
    signature   = $sig
}
$res4 = Test-IntentEnvelope -Envelope $env4
if ($res4.ok) { Write-Host "[PASS] v1 Still Supported" -ForegroundColor Green } else { Write-Error "Test 4 Failed: $($res4.reason)" }

Write-Host "`n>>> Verification Complete" -ForegroundColor Cyan
