$ErrorActionPreference = "Stop"
Import-Module "D:\Infinite\Infinity\Truth_Engine\T08_EnvelopeVerifier.psm1" -Force

# From sig_debug.txt
$SigA = "hmac256:5204a120f26325727c092b57ff573155a79d503aabeded0a9ecae17e6b29ce15" 
$SigLen = $SigA.Length # 72
$HexLen = ("5204a120f26325727c092b57ff573155a79d503aabeded0a9ecae17e6b29ce15").Length # 64

Write-Host "SigLen: $SigLen"

$Env = [pscustomobject]@{
    schema          = "axis.intent_envelope.v0.1"
    ts_utc          = (Get-Date).ToUniversalTime().ToString("o")
    nonce           = "TEST_NONCE_DIRECT"
    identity        = "portal:voice_local"
    input_signature = $SigA
    signature       = $SigA # The property T08 reads
    intent_json     = "{}"
}

# We need a valid secret to pass signature mismatch, 
# but here we just want to see if it passes 'bad_signature_format'.
# The signature won't match the payload (since I just made up payload), 
# so we expect 'signature_mismatch', NOT 'bad_signature_format'.

$Result = Test-IntentEnvelope -Envelope $Env
Write-Host "Result: $($Result.reason)"

if ($Result.reason -eq "bad_signature_format") {
    Write-Host "FAIL: Bad Signature Format" -ForegroundColor Red
}
elseif ($Result.reason -eq "signature_mismatch") {
    Write-Host "PASS: Format OK (Mismatch expected)" -ForegroundColor Green
}
else {
    Write-Host "Other: $($Result.reason)"
}
