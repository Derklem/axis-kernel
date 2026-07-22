# Axis_External_Anchor.ps1
# Phase 45: Creates and dispatches external anchors to witness channels.

param(
    [string]$Type = "DAILY_EXTERNAL_ANCHOR",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$TruthDir = Join-Path $Root "Truth_Engine"
$LockFile = Join-Path $Root "Runtime\Locks\external_anchor.lock"
$AnchorLedger = Join-Path $GovDir "external_anchor_ledger.jsonl"
$WitnessDir = Join-Path $GovDir "Witness"

# 1. Lock Acquisition
$lockStream = $null
try {
    if (-not (Test-Path (Split-Path $LockFile))) { New-Item -ItemType Directory (Split-Path $LockFile) -Force | Out-Null }
    $lockStream = [System.IO.File]::Open($LockFile, [System.IO.FileMode]::OpenOrCreate, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
}
catch {
    Write-Warning "Could not acquire external anchor lock. Skipping run."
    exit 0
}

try {
    Write-Host "--- AXIS EXTERNAL ANCHORING ($Type) ---" -ForegroundColor Cyan
    
    # 2. Compute State Vector
    $vectorJson = & (Join-Path $GovDir "Axis_Compute_StateVector.ps1")
    $vector = $vectorJson | ConvertFrom-Json
    
    # 3. Build Anchor Event
    $lastAnchorStr = $null
    if (Test-Path $AnchorLedger) { $lastAnchorStr = Get-Content $AnchorLedger | Select-Object -Last 1 }
    $lastAnchor = $null
    if (-not [string]::IsNullOrWhiteSpace($lastAnchorStr)) { $lastAnchor = $lastAnchorStr | ConvertFrom-Json }
    $prevHash = if ($lastAnchor) { $lastAnchor.hash } else { "GENESIS" }

    $anchor = [ordered]@{
        ts_utc        = (Get-Date).ToUniversalTime().ToString("o")
        anchor_id     = [Guid]::NewGuid().ToString()
        type          = $Type
        basis         = $vector
        channels      = @()
        previous_hash = $prevHash
    }

    # 4. Canonicalize Payload for Signing
    $payloadObj = [ordered]@{
        anchor_id = $anchor.anchor_id
        ts_utc    = $anchor.ts_utc
        basis     = $anchor.basis
    }
    $payloadRaw = $payloadObj | ConvertTo-Json -Compress
    
    # 5. Sign Payload
    Write-Host "Signing Anchor Pack..." -ForegroundColor Gray
    $sigResultJson = & (Join-Path $GovDir "Axis_Sign_Payload.ps1") -Payload $payloadRaw
    $sigResult = $sigResultJson | ConvertFrom-Json
    
    $anchor.signature = $sigResult.sig_base64
    $anchor.sig_alg   = $sigResult.sig_alg
    $anchor.key_id    = $sigResult.key_id

    # 6. Export Witness Pack (Phase 46)
    $packDir = Join-Path $WitnessDir "Packs\$($anchor.anchor_id)"
    if (-not (Test-Path $packDir)) { New-Item -ItemType Directory $packDir -Force | Out-Null }
    
    [System.IO.File]::WriteAllText((Join-Path $packDir "payload.txt"), $payloadRaw, [System.Text.Encoding]::UTF8)
    [System.IO.File]::WriteAllText((Join-Path $packDir "anchor_event.json"), ($anchor | ConvertTo-Json -Compress), [System.Text.Encoding]::UTF8)
    [System.IO.File]::WriteAllText((Join-Path $packDir "signature.b64"), $sigResult.sig_base64, [System.Text.Encoding]::UTF8)

    # 7. Dispatch Witness Channels
    
    # --- CHANNEL A: GIT WITNESS ---
    $gitChannel = [ordered]@{ name = "git"; status = "FAIL"; witness_ref = ""; details = "" }
    try {
        Set-Location $WitnessDir
        $isGit = git rev-parse --is-inside-work-tree 2>$null
        if ($isGit -ne "true") {
            git init | Out-Null
            git config user.name "Axis Sentinel"
            git config user.email "axis@infinity.local"
        }
        
        $dateKey = (Get-Date).ToString("yyyy-MM-dd")
        $witnessFile = "anchor_$($dateKey).jsonl"
        
        # Temporary entry for git commit (pre-hash)
        $tmpEntry = $anchor | ConvertTo-Json -Compress
        [System.IO.File]::AppendAllLines((Join-Path $WitnessDir $witnessFile), [string[]]@($tmpEntry))
        
        # Add the pack to git
        git add "Packs/$($anchor.anchor_id)/*"
        git add $witnessFile
        git commit -m "Axis Signed Anchor Pack: $($anchor.anchor_id)" | Out-Null
        $commitHash = git rev-parse HEAD
        
        $gitChannel.status = "SUCCESS"
        $gitChannel.witness_ref = $commitHash
    }
    catch {
        $gitChannel.details = $_.Exception.Message
    }
    $anchor.channels += $gitChannel

    # --- CHANNEL B: REMOTE GIT (Simulation) ---
    $remoteChannel = [ordered]@{ name = "remote_git"; status = "FAIL"; witness_ref = ""; details = "" }
    # Simulation: Log to a "remote" flat file to represent off-host diversity
    try {
        $remoteLog = Join-Path $Root "Runtime\Logs\remote_witness_sim.jsonl"
        $remoteEntry = [ordered]@{ ts_utc = $anchor.ts_utc; anchor_id = $anchor.anchor_id; commit = $gitChannel.witness_ref } | ConvertTo-Json -Compress
        [System.IO.File]::AppendAllLines($remoteLog, [string[]]@($remoteEntry))
        $remoteChannel.status = "SUCCESS"
        $remoteChannel.witness_ref = "sim-$(Get-Random)"
    } catch { $remoteChannel.details = $_.Exception.Message }
    $anchor.channels += $remoteChannel

    # 4. Compute Byte-Faithful Hash (AFTER dispatch/signing)
    $jsonForHash = $anchor | ConvertTo-Json -Compress
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $h = [System.BitConverter]::ToString($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($jsonForHash))).Replace("-", "").ToLower()
        $anchor.hash = $h
    }
    finally { $sha.Dispose() }

    # 8. Commit to Local Ledger
    $anchorJson = $anchor | ConvertTo-Json -Compress
    [System.IO.File]::AppendAllLines($AnchorLedger, [string[]]@($anchorJson))
    
    Write-Host "External Anchor Committed: $($anchor.anchor_id)" -ForegroundColor Green
    if ($gitChannel.status -eq "SUCCESS") { Write-Host "  -> Git Witness: $($gitChannel.witness_ref)" -ForegroundColor Gray }

}
finally {
    if ($lockStream) { $lockStream.Dispose() }
}
