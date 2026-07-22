<#
.SYNOPSIS
  Voice Intent Bridge
.DESCRIPTION
  Monitors voice_inbox.jsonl for new utterances.
  Maps allowed commands to SIGNED PROPOSAL ENVELOPES.
  Writes to voice_proposals.jsonl (does NOT inject into intent_queue directly).
.NOTES
  Identity: portal:voice_local
  Secret: axis_voice_secret_002
#>

[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity"
)

$ErrorActionPreference = "Stop"

# --- Configuration ---
$VoiceDir = Join-Path $Root "Runtime\Decision\Voice"
$InboxPath = Join-Path $VoiceDir "voice_inbox.jsonl"
$OutboxPath = Join-Path $VoiceDir "voice_proposals.jsonl"
$IdentityPath = Join-Path $Root "Truth_Engine\identity_registry.json"

# --- Identity ---
if (-not (Test-Path $IdentityPath)) { throw "Missing identity registry" }
$reg = Get-Content $IdentityPath -Raw | ConvertFrom-Json
$myId = $reg.identities | Where-Object { $_.identity -eq "portal:voice_local" }
if (-not $myId) { throw "Identity portal:voice_local not found in registry" }
$Secret = $myId.secret

# --- Helper Functions ---
function Hmac256([string]$key, [string]$msg) {
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($key))
    $bytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($msg))
    ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Create-Envelope($payload, $ttlSeconds = 900) {
    $now = (Get-Date).ToUniversalTime()
    $ts = $now.ToString("o")
    $expires = $now.AddSeconds($ttlSeconds).ToString("o")
    $nonce = [guid]::NewGuid().ToString()
    $payloadJson = $payload | ConvertTo-Json -Compress -Depth 10
    
    # Sign: ts_utc | nonce | identity | intent_json
    # T08_EnvelopeVerifier expects: "$ts|$nonce|$identity|$intentJson"
    $sigWait = "${ts}|${nonce}|portal:voice_local|${payloadJson}"
    $sig = Hmac256 $Secret $sigWait

    return [ordered]@{
        schema = "axis.intent_envelope.v0.1"
        ts_utc = $ts
        expires_utc = $expires
        nonce = $nonce
        identity = "portal:voice_local"
        signature = ("hmac256:" + $sig)
        intent_json = $payloadJson
    }
}

# --- Grammar Map ---
function Map-Utterance($text) {
    $t = $text.Trim().ToLower()
    
    if ($t -match "^status") {
        return [ordered]@{
            intent_id = "VOICE-STATUS-" + (New-Guid).ToString().Substring(0,8)
            type = "POST"
            target = "moltbook:voice_confirm"
            action = "post"
            payload = [ordered]@{
                title = "Voice Status Check"
                content = "System OK. Voice integration verified."
            }
            notes = "Voice triggered status check"
            review = [ordered]@{
                status = "pending"
                required = $true
            }
        }
    }
    
    if ($t -match "^note\s+(.+)") {
        return @{
            type = "PROPOSAL"
            target = "system:memory"
            action = "append_note"
            params = @{ content = $matches[1] }
        }
    }

    return $null
}

# --- Main Loop (One-Pass for now, extend to loop later) ---
if (-not (Test-Path $InboxPath)) { Write-Warning "No inbox"; exit }

# Read existing proposals to avoid dupes? 
# For v0.1 we just process last line of inbox if checking specific interaction, 
# but a real bridge would track a cursor. 
# Here we will just process the tail for testing.

$newest = Get-Content $InboxPath -Tail 1
if (-not $newest) { exit }

try {
    $utt = $newest | ConvertFrom-Json
    # Check if this utterance ID is already processed? 
    # TODO: Add cursor tracking. For now, we blindly map.
    
    $intent = Map-Utterance $utt.text
    if ($intent) {
        # Wrap in REVIEW PENDING
        $intent.review = @{
            required = $true
            status = "pending"
        }
        
        $ttl = 900 # Default 15m
        if ($intent.target -eq "system:memory") { $ttl = 86400 } # 24h for notes
        
        $env = Create-Envelope $intent $ttl
        $json = $env | ConvertTo-Json -Compress
        
        # Append to Outbox
        [System.IO.File]::AppendAllText($OutboxPath, $json + "`n", [System.Text.Encoding]::UTF8)
        Write-Host "Processed: $($utt.text) -> PROPOSAL (nonce: $($env.nonce))" -ForegroundColor Green
    } else {
        Write-Host "Ignored: $($utt.text)" -ForegroundColor Gray
    }
} catch {
    Write-Warning "Failed to parse inbox line"
}
