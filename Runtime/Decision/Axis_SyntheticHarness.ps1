param(
    [string]$RunProfile = "HEARTBEAT", # HEARTBEAT, EDGE, REHEARSAL
    [string]$QueueName = "sandbox_queue",
    [string]$Root = "D:\Infinite\Infinity",
    [int]$IntervalSeconds = 10,
    [int]$MaxCycles = 0 # 0 = Infinite
)

$ErrorActionPreference = "Stop"

# Paths
$RuntimeDir = Join-Path $Root "Runtime\Decision"
$QueueFile = Join-Path $RuntimeDir "$QueueName.jsonl"
$DecLog = Join-Path $RuntimeDir "decision_log.jsonl"
$StopConfig = Join-Path $RuntimeDir "Axis_Harness_StopConditions.json"
$IdentityFile = Join-Path $Root "Truth_Engine\identity_registry.json"

Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1

# Load Registry for Identity Metadata
if (-not (Test-Path $IdentityFile)) { throw "Identity registry missing" }
$reg = Get-Content $IdentityFile -Raw | ConvertFrom-Json

# --- Crypto Helper ---
function Compute-HmacSha256Hex($secret, $payload) {
    $enc = [System.Text.Encoding]::UTF8
    $keyBytes = $enc.GetBytes($secret)
    $msgBytes = $enc.GetBytes($payload)
    $h = [System.Security.Cryptography.HMACSHA256]::new($keyBytes)
    $hashBytes = $h.ComputeHash($msgBytes)
    return ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

$HarnessIdentity = "system:harness"
$harnessEntry = $reg.identities | Where-Object { $_.identity -eq $HarnessIdentity }
if (-not $harnessEntry) { throw "Harness identity not found in registry" }

function Get-RandomIntent {
    param($type) # VALID, EDGE_BAD_SIG, EDGE_EXPIRED, EDGE_NO_NONCE, EDGE_BAD_INTENT
    
    $ts = (Get-Date).ToUniversalTime().ToString("o")
    $nonce = [Guid]::NewGuid().ToString()
    $payloadObj = @{ op = "noop:heartbeat"; val = (Get-Random) }
    $intentJson = $payloadObj | ConvertTo-Json -Compress
    
    $identity = $HarnessIdentity
    $secret = Get-AxisSecret -KeyRef $harnessEntry.key_ref
    if (-not $secret) { throw "Could not fetch harness secret from KeyRing" }
    
    # Mutation: Expired
    if ($type -eq "EDGE_EXPIRED") {
        $ts = (Get-Date).ToUniversalTime().AddHours(-24).ToString("o")
    }
    
    # Mutation: No Nonce
    if ($type -eq "EDGE_NO_NONCE") {
        $nonce = ""
    }

    # Sign (Correctly)
    $sigPayload = "${ts}|${nonce}|${identity}|${intentJson}"
    $sigHex = Compute-HmacSha256Hex $secret $sigPayload
    
    # Mutation: Bad Sig
    if ($type -eq "EDGE_BAD_SIG") {
        $sigHex = $sigHex.Replace("a", "b").Replace("1", "2")
    }

    # Internal Intent Corruption (after signing)
    if ($type -eq "EDGE_BAD_INTENT") {
        $intentJson = "{ broken_json: "
    }

    return [ordered]@{
        schema      = "axis.intent_envelope.v0.1"
        ts_utc      = $ts
        nonce       = $nonce
        identity    = $identity
        sig_alg     = "hmac256"
        key_id      = $harnessEntry.key_id
        input_hash  = "mock_hash"
        intent_json = $intentJson
        signature   = "hmac256:" + $sigHex
    }
}

function Check-StopConditions {
    $logs = Get-Content $DecLog -Tail 20 -ErrorAction SilentlyContinue
    foreach ($line in $logs) {
        $Conditions = if (Test-Path $StopConfig) { Get-Content $StopConfig -Raw | ConvertFrom-Json } else { @{ forbidden_events = @("AUTHORITY_HASH_MISMATCH") } }
        foreach ($bad in $Conditions.forbidden_events) {
            if ($line -match $bad) {
                Write-Host "FATAL: Forbidden Event Detected: $bad" -ForegroundColor Red
                # ... triage logic ...
                exit 1
            }
        }
    }
}

Write-Host "Starting Access Synthetic Harness [$RunProfile] -> $QueueName (KeyRing Active)" -ForegroundColor Cyan

$cycle = 0
while ($true) {
    if ($MaxCycles -gt 0 -and $cycle -ge $MaxCycles) { break }
    $cycle++
    
    $intent = $null
    if ($RunProfile -eq "HEARTBEAT") {
        $rnd = Get-Random -Maximum 100
        if ($rnd -lt 90) { $intent = Get-RandomIntent "VALID" }
        else { $intent = Get-RandomIntent "EDGE_BAD_SIG" }
    }
    elseif ($RunProfile -eq "EDGE") {
        $types = @("EDGE_BAD_SIG", "EDGE_EXPIRED", "EDGE_NO_NONCE", "EDGE_BAD_INTENT")
        $t = $types[$cycle % $types.Count]
        $intent = Get-RandomIntent $t
    }

    if ($intent) {
        $json = $intent | ConvertTo-Json -Compress
        [System.IO.File]::AppendAllText($QueueFile, $json + "`n", [System.Text.Encoding]::UTF8)
        Write-Host "[$((Get-Date).ToString("HH:mm:ss"))] Injected Envelope ($RunProfile)" -ForegroundColor Gray
    }

    if ($cycle % 5 -eq 0) { Check-StopConditions }
    Start-Sleep -Seconds $IntervalSeconds
}
