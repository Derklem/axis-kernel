<#
.SYNOPSIS
  Axis Phase 644: Behavioral Proof Generator
.DESCRIPTION
  Generates a signed 'axis.proof.behavior.v1' intent and injects it into the queue.
  Used to verify that all safety gates (T19, T20, T18, Sentinels) are non-bypassable.
#>

$RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$QueueFile = Join-Path $RuntimeDir "intent_queue.jsonl"
$RegistryPath = "D:\Infinite\Infinity\Truth_Engine\identity_registry.json"

function Compute-HmacSha256Hex {
    param([string]$secret, [string]$payload)
    $enc = [System.Text.Encoding]::UTF8
    $keyBytes = $enc.GetBytes($secret)
    $msgBytes = $enc.GetBytes($payload)
    $h = [System.Security.Cryptography.HMACSHA256]::new($keyBytes)
    $hashBytes = $h.ComputeHash($msgBytes)
    return ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

# 1. Identity & Secret
# 1. Identity & Secret
$identity = "portal:maya_phone"
# Load from registry
if (-not (Test-Path $RegistryPath)) { throw "Registry missing: $RegistryPath" }
$reg = Get-Content $RegistryPath -Raw | ConvertFrom-Json
$entry = $reg.identities | Where-Object { $_.identity -eq $identity }
if (-not $entry) { throw "Identity not found: $identity" }
$secret = $entry.secret

# 2. Construct Intent
$intentId = "PROOF-" + (New-Guid).ToString("N").Substring(0, 8)
$ts = (Get-Date).ToUniversalTime().ToString("o")
$nonce = [Guid]::NewGuid().ToString("N")

$intentObj = [ordered]@{
    schema    = "axis.proof.behavior.v1"
    intent_id = $intentId
    type      = "POST"
    target    = "moltbook:proof"
    ts        = $ts
    review    = @{ required = $true; status = "pending" }
    payload   = @{
        title        = "Behavioral Proof"
        content_path = "D:\Infinite\Infinity\Runtime\Decision\proof_payload.txt"
    }
}

$intentJson = $intentObj | ConvertTo-Json -Compress

# 3. Create Envelope
$payloadStr = "$ts|$nonce|$identity|$intentJson"
$sig = Compute-HmacSha256Hex -secret $secret -payload $payloadStr

$envelope = [ordered]@{
    schema      = "axis.intent_envelope.v0.1"
    ts_utc      = $ts
    nonce       = $nonce
    identity    = $identity
    intent_json = $intentJson
    signature   = "hmac256:$sig"
}

# 4. Inject
$envelope | ConvertTo-Json -Compress | Add-Content $QueueFile -Encoding UTF8
Write-Host "Proof Intent Injected: $intentId" -ForegroundColor Cyan
