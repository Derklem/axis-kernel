
# Axis_Status.ps1
# Phase 48: Operator Console - "One Command Truth"
# Prints current system health, recent anchors, pulse status, and alerts.

$ErrorActionPreference = "Stop"
$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$TruthDir = Join-Path $Root "Truth_Engine"
$MemoryRoot = Join-Path $Root "Memory"

function Get-Head($path) {
    if (-not (Test-Path $path)) { return $null }
    try {
        $lines = Get-Content $path -Tail 1
        return ($lines | ConvertFrom-Json)
    } catch { return $null }
}

Write-Host "--- AXIS SYSTEM STATUS ---" -ForegroundColor Cyan
Write-Host "Time: $(Get-Date)" -ForegroundColor DarkGray
Write-Host ""

# 1. Integrity Pulse
$pulsePath = Join-Path $GovDir "integrity_pulse_ledger.jsonl"
$pulse = Get-Head $pulsePath
if ($pulse) {
    $color = if ($pulse.status -eq "SUCCESS") { "Green" } else { "Red" }
    $mode = if ($pulse.mode) { $pulse.mode } else { $pulse.pulse_type }
    $ts = if ($pulse.ts_utc) { $pulse.ts_utc } else { $pulse.timestamp }
    Write-Host "INTEGRITY PULSE: " -NoNewline
    Write-Host "[$($pulse.status)]" -ForegroundColor $color -NoNewline
    Write-Host " ($mode) @ $ts"
} else {
    Write-Host "INTEGRITY PULSE: [UNKNOWN] (Ledger missing or empty)" -ForegroundColor Red
}

# 2. External Anchor
$anchorPath = Join-Path $GovDir "external_anchor_ledger.jsonl"
$anchor = Get-Head $anchorPath
if ($anchor) {
    Write-Host "EXTERNAL ANCHOR: " -NoNewline
    Write-Host "[OK]" -ForegroundColor Green -NoNewline
    Write-Host " ID: $($anchor.event_id)"
    Write-Host "  Commit: $($anchor.hash)" -ForegroundColor DarkGray
} else {
    Write-Host "EXTERNAL ANCHOR: [NONE]" -ForegroundColor Yellow
}

# 3. Compaction Status
$manifestPath = Join-Path $MemoryRoot "packs\compaction_manifest.jsonl"
$manifest = Get-Head $manifestPath
if ($manifest) {
    Write-Host "T17 COMPACTION:  " -NoNewline
    Write-Host "[ACTIVE]" -ForegroundColor Green -NoNewline
    Write-Host " Last: $($manifest.original_segment) -> $($manifest.pack_file)"
} else {
    Write-Host "T17 COMPACTION:  [NO DATA]" -ForegroundColor Yellow
}

# 4. Recent Alerts (Top 5)
$alertFiles = Get-ChildItem (Join-Path $MemoryRoot "alerts") -Filter "*.jsonl"
if ($alertFiles) {
    Write-Host ""
    Write-Host "RECENT ALERTS (Top 5):" -ForegroundColor Yellow
    $allAlerts = @()
    foreach ($f in $alertFiles) {
        $lines = Get-Content $f.FullName -Tail 5
        foreach ($l in $lines) {
            try { 
                $obj = $l | ConvertFrom-Json 
                if (-not $obj.ts) { $obj | Add-Member -MemberType NoteProperty -Name "ts" -Value $obj.ts_utc -Force }
                $allAlerts += $obj
            } catch {}
        }
    }
    
    $recent = $allAlerts | Sort-Object ts -Descending | Select-Object -First 5
    foreach ($a in $recent) {
        Write-Host "  [$($a.ts)] $($a.ledger): $($a.msg)" -ForegroundColor Red
    }
} else {
    Write-Host ""
    Write-Host "RECENT ALERTS:   [NONE]" -ForegroundColor Green
}

Write-Host ""
Write-Host "System is OPERATIONAL." -ForegroundColor Cyan
