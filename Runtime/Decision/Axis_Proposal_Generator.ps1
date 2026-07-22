<#
.SYNOPSIS
  Axis Proposal Generator
.DESCRIPTION
  Scans system logs (ingest errors, drift heartbeat) and generates PROPOSAL intents
  for the user to review. Outputs to voice_proposals.jsonl for safety.
.NOTES
  Source: AXIS-GEN
#>

[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity",
    [int]$LookbackMinutes = 60
)

$ErrorActionPreference = "Continue" # Changed to Continue to allow debug prints

# --- Paths ---
$Runtime = Join-Path $Root "Runtime\Decision"
$Memory = Join-Path $Root "Memory\ledger"
$VoiceOutbox = Join-Path $Runtime "Voice\voice_proposals.jsonl"

$IngestErrors = Join-Path $Memory "ingest_errors.jsonl"
$DriftLog = Join-Path $Runtime "drift_heartbeat.jsonl"

# --- Thresholds ---
$MaxIngestErrors = 5
$MaxDriftFailures = 0

# --- State Helpers ---
function Get-Recent-Count([string]$path, [int]$minutes) {
    if (-not (Test-Path $path)) { return 0 }
    $cutoff = (Get-Date).AddMinutes(-$minutes).ToUniversalTime()
    $count = 0
    try {
        Get-Content $path -Tail 100 | ForEach-Object {
            try {
                $e = $_ | ConvertFrom-Json
                # Handle different timestamp fields
                $tsStr = if ($e.ts_utc) { $e.ts_utc } elseif ($e.ts) { $e.ts } else { $null }
                if ($tsStr) {
                    $ts = [DateTime]::Parse($tsStr).ToUniversalTime()
                    if ($ts -ge $cutoff) { $count++ }
                }
            }
            catch { Write-Warning "Parse Error in $path : $_" }
        }
    }
    catch { Write-Warning "Read Error in $path : $_" }
    return $count
}

function Get-Recent-Failures([string]$path, [int]$minutes) {
    if (-not (Test-Path $path)) { return 0 }
    $cutoff = (Get-Date).AddMinutes(-$minutes).ToUniversalTime()
    $fails = 0
    try {
        Get-Content $path -Tail 50 | ForEach-Object {
            try {
                $e = $_ | ConvertFrom-Json
                $ts = [DateTime]::Parse($e.ts).ToUniversalTime()
                if ($ts -ge $cutoff -and $e.exit_code -ne 0) { $fails++ }
            }
            catch { Write-Warning "Parse Error in $path : $_" }
        }
    }
    catch { Write-Warning "Read Error in $path : $_" }
    return $fails
}

# --- Logic ---

$proposals = @()

# 1. Ingest Errors
$errCount = Get-Recent-Count $IngestErrors $LookbackMinutes
if ($errCount -gt $MaxIngestErrors) {
    Write-Host "Detected $errCount ingest errors." -ForegroundColor Yellow
    $proposals += @{
        text     = "Analyze Data Corruption ($errCount errors)"
        domain   = "maintenance"
        task     = "repair_memory"
        priority = "high"
    }
}

# 2. Drift Failures
$driftFails = Get-Recent-Failures $DriftLog $LookbackMinutes
if ($driftFails -gt $MaxDriftFailures) {
    Write-Host "Detected $driftFails drift failures." -ForegroundColor Yellow
    $proposals += @{
        text     = "Run System Diagnostics (Drift Detected)"
        domain   = "maintenance"
        task     = "system_diagnostic"
        priority = "critical"
    }
}

# --- Output ---

if ($proposals.Count -eq 0) {
    Write-Host "No new proposals generated." -ForegroundColor Green
    return
}

foreach ($p in $proposals) {
    $id = "GEN-PROP-" + (New-Guid).ToString().Substring(0, 8)
    $intent = @{
        intent_id   = $id
        proposal_id = $id
        type        = "PROPOSAL"
        source      = "AXIS-GEN"
        ts_utc      = (Get-Date).ToUniversalTime().ToString("o")
        intent      = $p
        status      = "PENDING_REVIEW"
        confidence  = 1.0
        nonce       = $id # For Review Manager compatibility
    }
    
    # Wrap in Envelope (Phase 648 Standard)
    $intentJsonString = $intent | ConvertTo-Json -Compress -Depth 10 # Canonical JSON
    
    $ts = (Get-Date).ToUniversalTime().ToString("o")
    $nonce = $id
    $identity = "system:generator"
    
    $envelope = [ordered]@{
        schema      = "axis.intent_envelope.v0.1"
        ts_utc      = $ts
        # Generator proposals expire in 24h
        expires_utc = (Get-Date).AddHours(24).ToUniversalTime().ToString("o")
        nonce       = $nonce
        identity    = $identity
        signature   = "internal:generated"
        intent_json = $intentJsonString
    }
    
    $outJson = $envelope | ConvertTo-Json -Compress
    
    # Check for duplicates (naive check on text in intent_json)
    if (Test-Path $VoiceOutbox) {
        $exists = Select-String -Path $VoiceOutbox -Pattern $p.text -SimpleMatch -Quiet
        if ($exists) {
            Write-Warning "Skipping duplicate proposal: $($p.text)"
            continue
        }
    }
    
    $outJson | Add-Content $VoiceOutbox -Encoding UTF8
    Write-Host "Generated Proposal: [$id] $($p.text)" -ForegroundColor Cyan
}
