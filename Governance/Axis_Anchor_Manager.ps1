# Axis_Anchor_Manager.ps1
# Phase 41: Daily Multi-Ledger Anchoring
# Captures the head hash of each hot ledger and persists it to a tamper-evident anchor chain.

$ErrorActionPreference = "Stop"

$Root = "D:\Infinite\Infinity"
$TruthDir = Join-Path $Root "Truth_Engine"
$GovDir = Join-Path $Root "Governance"
$AnchorLedger = Join-Path $GovDir "anchor_ledger.jsonl"

# Import T17 for Get-LedgerHeadHash
$T17Path = Join-Path $TruthDir "T17_MemoryIndexer.psm1"
if (Test-Path $T17Path) {
    Import-Module $T17Path -Force
}
else {
    Write-Error "T17_MemoryIndexer.psm1 not found at $T17Path"
    return
}

$Ledgers = @(
    @{ name = "audit"; path = Join-Path $TruthDir "audit_trail.jsonl" },
    @{ name = "spend"; path = Join-Path $TruthDir "spend_ledger.jsonl" },
    @{ name = "decision"; path = Join-Path $Root "Runtime\Decision\decision_log.jsonl" },
    @{ name = "policy"; path = Join-Path $GovDir "policy_update_ledger.jsonl" }
)

$AnchorLog = Join-Path $GovDir "anchor_manager.trace.log"
Start-Transcript -Path $AnchorLog -Force

Write-Host "--- AXIS ANCHOR MANAGER ---" -ForegroundColor Cyan

try {
    # 1. Get Previous Anchor Hash (Global chain)
    $prevAnchorHash = "genesis"
    if (Test-Path $AnchorLedger) {
        # Efficiently read last line using System.IO to avoid Get-Content memory hit for large logs
        $fs = [System.IO.File]::Open($AnchorLedger, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        try {
            if ($fs.Length -gt 0) {
                $seekSize = [Math]::Min(2048, $fs.Length)
                $fs.Seek(-$seekSize, [System.IO.SeekOrigin]::End) | Out-Null
                $reader = New-Object System.IO.StreamReader($fs)
                $lines = $reader.ReadToEnd() -split "\r?\n"
                $lastLine = $lines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 1
                if ($lastLine) {
                    $lastAnchor = $lastLine | ConvertFrom-Json
                    $prevAnchorHash = $lastAnchor.hash
                }
            }
        } finally { $fs.Dispose() }
    }

    $newAnchors = @()
    $tsLine = (Get-Date).ToString("o")

    foreach ($l in $Ledgers) {
        if (-not (Test-Path $l.path)) {
            Write-Host "  [SKIP] Ledger file not found: $($l.name)" -ForegroundColor Yellow
            continue
        }

        $head = Get-LedgerHeadHash -Path $l.path
        if ($null -eq $head) {
            Write-Host "  [SKIP] No readable entries in $($l.name)." -ForegroundColor Yellow
            continue
        }

        $anchorEntry = [ordered]@{
            ts              = $tsLine
            ledger          = $l.name
            head_event_id   = $head.LastEventId
            head_event_hash = $head.LastEventHash
            previous_hash   = $prevAnchorHash
        }
        
        # Compute anchor hash
        $json = $anchorEntry | ConvertTo-Json -Compress
        $anchorHash = "sha256:" + (Get-Sha256Bytes -Bytes ([System.Text.Encoding]::UTF8.GetBytes($json)))
        
        $anchorEntry.hash = $anchorHash
        $newAnchors += $anchorEntry | ConvertTo-Json -Compress
        
        # Chain the anchors within this run
        $prevAnchorHash = $anchorHash
        Write-Host "  [OK] Anchored $($l.name) head: $($head.LastEventHash)" -ForegroundColor Green
    }

    Write-Host "DEBUG: Loop finished. newAnchors.Count = $($newAnchors.Count)"
    if ($newAnchors.Count -gt 0) {
        $linesToWrite = [string[]]$newAnchors
        Write-Host "DEBUG: Committing to $AnchorLedger"
        [System.IO.File]::AppendAllLines($AnchorLedger, $linesToWrite)
        Write-Host "Successfully committed $($linesToWrite.Count) anchor(s) to $AnchorLedger." -ForegroundColor Cyan
    } else {
        Write-Host "No ledgers were anchored." -ForegroundColor Yellow
    }
}
finally {
    Stop-Transcript
}
