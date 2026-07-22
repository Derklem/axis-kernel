<#
.SYNOPSIS
  Axis Review Manager
.DESCRIPTION
  Manages the lifecycle of system proposals.
  Allows approving/rejecting proposals by signing an intent_sha256 with a governance key.
.NOTES
  Identity: portal:maya_phone
#>

[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity",
    [string]$Action, # APPROVE | REJECT | LIST
    [string]$ProposalId,
    [string]$Reason = "Manual Review"
)

$ErrorActionPreference = "Stop"

# --- Paths ---
$Runtime = Join-Path $Root "Runtime\Decision"
$ReviewDir = Join-Path $Runtime "Review"
$LogPath = Join-Path $ReviewDir "review_log.jsonl"
$VoiceOutbox = Join-Path $Runtime "Voice\voice_proposals.jsonl"
$IdentityPath = Join-Path $Root "Truth_Engine\identity_registry.json"

# --- Helpers ---
function Read-Registry {
    if (-not (Test-Path $IdentityPath)) { throw "Missing identity registry" }
    return (Get-Content $IdentityPath -Raw | ConvertFrom-Json)
}

function Compute-Sha256([string]$StringContent) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($StringContent)
    $hash = $sha.ComputeHash($bytes)
    return ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Hmac256([string]$key, [string]$msg) {
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($key))
    $bytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($msg))
    return ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

# --- Actions ---
if ($Action -eq "LIST") {
    if (-not (Test-Path $LogPath)) { Write-Host "Log empty."; return }
    Get-Content $LogPath -Tail 100 -Encoding UTF8 | ForEach-Object { ConvertFrom-Json $_ } | Format-Table ts, action, proposal_id, actor, reason
    return
}

if (-not $ProposalId) { throw "ProposalId required for $Action" }

if ($Action -eq "APPROVE") {
    # 1. Find proposal
    $found = $null
    if (Test-Path $VoiceOutbox) {
        $found = Get-Content $VoiceOutbox | Select-String -Pattern $ProposalId | Select-Object -First 1 | ForEach-Object { $_.Line | ConvertFrom-Json }
    }
    
    if (-not $found -or $found.nonce -ne $ProposalId) {
        # Fallback: check case-insensitive or guid match
        $all = Get-Content $VoiceOutbox | ForEach-Object { try { ConvertFrom-Json $_ } catch {} }
        $found = $all | Where-Object { 
            if ($_.nonce -eq $ProposalId) { return $true }
            if ($_.intent_json) {
                try {
                    $inner = $_.intent_json | ConvertFrom-Json
                    if ($inner.intent_id -eq $ProposalId) { return $true }
                }
                catch {}
            }
            return $false
        } | Select-Object -First 1
    }
    
    if (-not $found) { throw "Proposal [$ProposalId] not found in outbox." }
    
    # Canonicalize ID to Nonce (Phase 20)
    $CanonicalId = $found.nonce
    if ([string]::IsNullOrWhiteSpace($CanonicalId)) { throw "Envelope missing nonce - cannot approve." }
    
    # 2. Extract Intent and Hash it
    $intentJson = if ($found.intent_json) { $found.intent_json } else { $found.payload | ConvertTo-Json -Compress -Depth 10 }
    
    if ([string]::IsNullOrWhiteSpace($intentJson)) { throw "Extracted intent_json is empty!" }
    Write-Host "DEBUG: intent_json length: $($intentJson.Length)" -ForegroundColor Gray
    
    $intentSha = Compute-Sha256 $intentJson
    
    # SAFETY: Block empty string hash (e3b0c442...)
    if ($intentSha -eq "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855") {
        throw "SECURITY FATAL: Refusing to approve empty-string hash."
    }
    
    Write-Host "Intent Hash: $intentSha" -ForegroundColor Cyan
    
    # 3. Get Governor Secret
    $reg = Read-Registry
    $maya = $reg.identities | Where-Object { $_.identity -eq "portal:maya_phone" }
    if (-not $maya) { throw "Maya identity not found." }
    
    # 4. Create Event
    $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.000000Z")
    $event = [ordered]@{
        schema        = "axis.review.event.v1"
        ts            = $ts
        proposal_id   = $CanonicalId
        action        = "APPROVED"
        actor         = "portal:maya_phone"
        intent_sha256 = $intentSha
        reason        = $Reason
    }
    
    # 5. Sign: ts | proposal_id | action | sha256
    $sigWait = "${ts}|$CanonicalId|APPROVED|$intentSha"
    $event.signature = ("hmac256:" + (Hmac256 $maya.secret $sigWait))
    
    # 6. Commit
    $line = $event | ConvertTo-Json -Compress
    [System.IO.File]::AppendAllText($LogPath, $line + "`n", [System.Text.Encoding]::UTF8)
    Write-Host "SUCCESS: Proposal $ProposalId approved." -ForegroundColor Green
}
