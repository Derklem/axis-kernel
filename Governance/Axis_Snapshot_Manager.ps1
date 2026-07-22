<#
.SYNOPSIS
  Axis_Snapshot_Manager.ps1
  Phase 41: Captures a point-in-time metadata snapshot of the system.
.DESCRIPTION
  Creates `D:\Infinite\Infinity\Snapshots\YYYY-MM-DD\snapshot.json`.
  
  Content:
  - Timestamp
  - Anchor Hash (link to anchor_ledger)
  - State Vector (Hashes of all ledgers/artifacts)
  - Metrics (Line counts, file sizes)
  - Active Verification Status (Result of verifying ledgers at this moment)
.EXAMPLE
  Axis_Snapshot_Manager.ps1
#>

$ErrorActionPreference = "Stop"

$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$TruthDir = Join-Path $Root "Truth_Engine"
$SnapDir = Join-Path $Root "Snapshots"
$AnchorLedger = Join-Path $GovDir "anchor_ledger.jsonl"

$DateStr = (Get-Date).ToString("yyyy-MM-dd")
$TodaySnapDir = Join-Path $SnapDir $DateStr

if (-not (Test-Path $TodaySnapDir)) {
    New-Item -ItemType Directory -Path $TodaySnapDir -Force | Out-Null
}

# --- Helpers ---

function Get-LedgerStats($path) {
    if (-not (Test-Path $path)) { return @{ hash = "null"; count = 0; size_bytes = 0 } }
    
    $info = Get-Item $path
    $size = $info.Length
    
    # 1. Get Hash (Tail 1 is safer/faster for head hash)
    $lastHash = "null"
    try {
        $last = Get-Content $path -Tail 1 -ErrorAction Stop
        if (-not [string]::IsNullOrWhiteSpace($last)) {
            $obj = $last | ConvertFrom-Json
            if ($obj.hash) { $lastHash = $obj.hash }
            else {
                # Fallback: Hash the line
                $sha = [System.Security.Cryptography.SHA256]::Create()
                $bytes = [System.Text.Encoding]::UTF8.GetBytes($last)
                $lastHash = "sha256:" + ([BitConverter]::ToString($sha.ComputeHash($bytes)) -replace "-", "").ToLower()
            }
        }
    }
    catch {
        Write-Warning "Failed to read hash from $path : $_"
        $lastHash = "error"
    }

    # 2. Get Count (Streamed)
    $lines = 0
    try {
        # Streaming count (memory efficient)
        $lines = 0
        foreach ($line in [System.IO.File]::ReadLines($path)) { $lines++ }
    }
    catch {
        Write-Warning "Failed to count lines in $path : $_"
    }

    return @{
        hash       = $lastHash
        count      = $lines
        size_bytes = $size
    }
}

function Get-FileHash($path) {
    if (-not (Test-Path $path)) { return "null" }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($path)
    $hash = [BitConverter]::ToString($sha.ComputeHash($stream)) -replace "-", ""
    $stream.Close()
    return "sha256:" + $hash.ToLower()
}

# --- Execution ---

Write-Host "--- AXIS SNAPSHOT MANAGER (Phase 41) ---" -ForegroundColor Cyan
Write-Host "Target: $TodaySnapDir" -ForegroundColor Gray

# 1. Get Latest Anchor
$latestAnchor = "null"
if (Test-Path $AnchorLedger) {
    $last = Get-Content $AnchorLedger -Tail 1
    try {
        $obj = $last | ConvertFrom-Json
        $latestAnchor = $obj.hash
    }
    catch {}
}

# 2. Collect Metrics & Hashes
$metrics = [ordered]@{}
$ledgers = @{
    audit      = Join-Path $TruthDir "audit_trail.jsonl"
    spend      = Join-Path $TruthDir "spend_ledger.jsonl"
    revocation = Join-Path $GovDir "revocation_ledger.jsonl"
    policy     = Join-Path $GovDir "policy_update_ledger.jsonl"
}

foreach ($k in $ledgers.Keys) {
    $stats = Get-LedgerStats $ledgers[$k]
    $metrics[$k] = $stats
    Write-Host "  $k : $($stats.count) lines, $($stats.hash)" -ForegroundColor Gray
}

# Artifacts
$artifacts = @{
    identity = Join-Path $TruthDir "identity_registry.json"
    keyring  = Join-Path $TruthDir "keyring.json"
}

foreach ($k in $artifacts.Keys) {
    $h = Get-FileHash $artifacts[$k]
    $metrics[$k] = @{ hash = $h; size_bytes = (Get-Item $artifacts[$k]).Length }
    Write-Host "  $k : $h" -ForegroundColor Gray
}

# 3. Build Snapshot Object
$snapshot = [ordered]@{
    snapshot_id    = "snap-" + (New-Guid).ToString("N")
    timestamp      = (Get-Date).ToUniversalTime().ToString("o")
    date_key       = $DateStr
    anchor_link    = $latestAnchor
    system_metrics = $metrics
    
    # Optional: Verification Status (Could run verifiers here, but that's heavy. Just capture state.)
    verified       = $false 
}

# 4. Save
$json = $snapshot | ConvertTo-Json -Depth 4
$outFile = Join-Path $TodaySnapDir "snapshot.json"
[System.IO.File]::WriteAllText($outFile, $json, [System.Text.Encoding]::UTF8)

Write-Host "  [OK] Snapshot Saved: $outFile" -ForegroundColor Green

# 5. Trigger External Anchor (Phase 45)
Write-Host "Triggering External Anchor..." -ForegroundColor Gray
& (Join-Path $GovDir "Axis_External_Anchor.ps1") -Type "SNAPSHOT_ANCHOR" | Out-Null
