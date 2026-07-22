$ErrorActionPreference = "Stop"
Import-Module "D:\Infinite\Infinity\Truth_Engine\T08_EnvelopeVerifier.psm1" -Force

Write-Host "--- Testing Registry Access ---"
$regPath = "D:\Infinite\Infinity\Truth_Engine\identity_registry.json"
$reg = Get-Content $regPath -Raw | ConvertFrom-Json
$harness = $reg.identities | Where-Object { $_.identity -eq "system:harness" }
if ($harness) {
    Write-Host "Found system:harness" -ForegroundColor Green
    Write-Host ($harness | ConvertTo-Json)
}
else {
    Write-Host "FAIL: system:harness NOT FOUND in registry object." -ForegroundColor Red
}

Write-Host "`n--- Testing Secret Lookup (Indirect via Verification) ---"
# We can't call Get-IdentitySecret directly, so we test verification.

Write-Host "`n--- Testing Synthetic Envelope ---"
# Define local helper instead of dot-sourcing the running harness
function Compute-HmacSha256Hex($secret, $payload) {
    $enc = [System.Text.Encoding]::UTF8
    $keyBytes = $enc.GetBytes($secret)
    $msgBytes = $enc.GetBytes($payload)
    $h = [System.Security.Cryptography.HMACSHA256]::new($keyBytes)
    $hashBytes = $h.ComputeHash($msgBytes)
    return ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

$intentJson = '{"op":"noop:heartbeat","val":123}'
$ts = (Get-Date).ToUniversalTime().ToString("o")
$nonce = [Guid]::NewGuid().ToString()
$identity = "system:harness"
# Use the secret we verified earlier? No, use known string to verify match
$secret = "axis_harness_secret_004"

$sigPayload = "${ts}|${nonce}|${identity}|${intentJson}"
$sigHex = Compute-HmacSha256Hex $secret $sigPayload

$envelope = [PSCustomObject]@{
    schema      = "axis.intent_envelope.v0.1"
    ts_utc      = $ts
    nonce       = $nonce
    identity    = $identity
    intent_json = $intentJson
    signature   = "hmac256:" + $sigHex
}

$res = Test-IntentEnvelope -Envelope $envelope
if ($res.ok) { 
    Write-Host "Envelope Verification: PASS" -ForegroundColor Green 
    Write-Host "Valid Identity: $($res.identity)"
}
else {
    Write-Host "Envelope Verification: FAIL ($($res.reason))" -ForegroundColor Red
}
