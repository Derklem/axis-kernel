Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1

$Identity = "system:harness"
$Secret = Get-AxisSecret -KeyRef 'dpapi:CURRENTUSER:axis:system_harness:v1'
if (-not $Secret) { throw "Secret not found" }

$ts = (Get-Date).ToUniversalTime().ToString("o")
$nonce = [Guid]::NewGuid().ToString()
$intentJson = '{"op":"policy:apply","val":"malicious_update"}'

$payload = "$ts|$nonce|$Identity|$intentJson"
$hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($Secret))
$sig = ($hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($payload)) | ForEach-Object { $_.ToString("x2") }) -join ""

$envelope = [ordered]@{
    schema      = "axis.intent_envelope.v0.1"
    ts_utc      = $ts
    nonce       = $nonce
    identity    = $Identity
    sig_alg     = "hmac256"
    key_id      = "k_system_harness_v1"
    input_hash  = "mock_hash"
    intent_json = $intentJson
    signature   = "hmac256:" + $sig
}

$envelope | ConvertTo-Json -Compress | Add-Content D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl
Write-Host "Unauthorized intent injected: $nonce" -ForegroundColor Yellow
