# T12_Checkpoint.ps1
# Generates a tamper-evident checkpoint for the Provenance Log.
# Run daily or on-pulse.

param($Commit = $true)

$LogPath = "D:\Infinite\Infinity\Runtime\Decision\provenance_events.jsonl"
$CheckpointPath = "D:\Infinite\Infinity\Runtime\Decision\provenance_checkpoint.json"

if (-not (Test-Path $LogPath)) { Write-Warning "Log not found"; exit }

# 1. Calculate Rolling Hash
# For v0.1: SHA256 of the entire file. 
# Future: Merkle Tree or Block Chain.

$algo = [System.Security.Cryptography.SHA256]::Create()
$fs = [System.IO.File]::OpenRead($LogPath)
$hashBytes = $algo.ComputeHash($fs)
$fs.Close()
$fileHash = [BitConverter]::ToString($hashBytes).Replace("-", "").ToLower()

# 2. Get Stats
$content = Get-Content $LogPath
$lineCount = $content.Count
$tailLine = if ($lineCount -gt 0) { $content[-1] } else { "" }
$tailHash = if ($tailLine) {
    $b = [System.Text.Encoding]::UTF8.GetBytes($tailLine)
    [BitConverter]::ToString($algo.ComputeHash($b)).Replace("-", "").ToLower().Substring(0, 16)
} else { "empty" }

# 3. Construct Checkpoint
$ckpt = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    log_file = "provenance_events.jsonl"
    line_count = $lineCount
    file_hash_sha256 = $fileHash
    tail_hash_16 = $tailHash
    schema_version = "axis.provenance.checkpoint.v0.1"
}

$json = $ckpt | ConvertTo-Json -Depth 5

Write-Host "Checkpoint Generated: Lines=$lineCount Hash=$($fileHash.Substring(0,8))..." -ForegroundColor Cyan

if ($Commit) {
    $json | Set-Content $CheckpointPath -Encoding UTF8 -Force
    Write-Host "Saved to $CheckpointPath" -ForegroundColor Green
} else {
    $json
}
