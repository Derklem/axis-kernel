<#
.SYNOPSIS
  T12_MorningReport.ps1 (L3.5)
.DESCRIPTION
  Generates a "Morning Report" Digest:
  - Trust Map Shifts (What I Learned)
  - Shadow Log Drafts (What I Dreamed)
  - Pressure Metrics (How I Felt)
.OUTPUT
  Writes to D:\Infinite\Infinity\Reports\Morning_Report_YYYYMMDD.md
#>

$RuntimeDir = "D:\Infinite\Infinity\Runtime"
$ReportDir = "D:\Infinite\Infinity\Reports"
if (-not (Test-Path $ReportDir)) { New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null }

$TrustLog = "$RuntimeDir\Listener\trust_update_log.jsonl"
$ShadowLog = "$RuntimeDir\Listener\shadow_log.jsonl"
$PressureLog = "$RuntimeDir\Epistemic\ece_pressure.json"

$DateStr = (Get-Date).ToString("yyyyMMdd")
$OutFile = Join-Path $ReportDir "Morning_Report_$DateStr.md"

# --- Helpers ---
function Get-RecentEvents($path, $hours = 24) {
    if (-not (Test-Path $path)) { return @() }
    $cut = (Get-Date).ToUniversalTime().AddHours(-$hours)
    $events = @()
    # Read last 1000 lines efficiently
    $lines = Get-Content $path -Tail 1000
    foreach ($l in $lines) {
        try {
            $e = $l | ConvertFrom-Json
            if ([DateTime]$e.ts -ge $cut) { $events += $e }
        }
        catch {}
    }
    return $events
}

# --- Data Gathering ---
$trustEvents = Get-RecentEvents $TrustLog
$shadowEvents = Get-RecentEvents $ShadowLog

$pressure = $null
if (Test-Path $PressureLog) { 
    try { $pressure = Get-Content $PressureLog -Raw | ConvertFrom-Json } catch {} 
}

# --- Report Generation ---
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Morning Report: $DateStr")
[void]$sb.AppendLine("**Generated at**: $((Get-Date).ToString("o"))")
[void]$sb.AppendLine("")

# 1. State of Mind (Pressure)
[void]$sb.AppendLine("## 1. State of Mind")
if ($pressure) {
    [void]$sb.AppendLine("- **Noise Level**: $($pressure.count) events (last $($pressure.window_min)m)")
    
    $avg = if ($pressure.avg_score) { $pressure.avg_score } else { "N/A" }
    [void]$sb.AppendLine("- **Confidence**: Avg Score **$avg**")
    
    $rate = if ($pressure.accept_rate) { [math]::Round($pressure.accept_rate * 100, 1) } else { 0 }
    [void]$sb.AppendLine("- **Accept Rate**: $rate%")
    
    # Status Logic
    if ($pressure.count -eq 0) {
        [void]$sb.AppendLine("> **Status**: **QUIET** (No recent signals)")
    }
    elseif ($pressure.avg_score -lt 70) {
        [void]$sb.AppendLine("> **Status**: **OBSERVANT** (High Pressure / Low Confidence)")
    }
    else {
        [void]$sb.AppendLine("> **Status**: **LUCID** (Clear Signal)")
    }
}
else {
    [void]$sb.AppendLine("No pressure data.")
}
[void]$sb.AppendLine("")

# 2. What I Learned (Trust Updates)
[void]$sb.AppendLine("## 2. What I Learned (Trust Map)")
if ($trustEvents.Count -gt 0) {
    $grouped = $trustEvents | Group-Object key
    foreach ($g in $grouped) {
        $first = $g.Group[0]
        $last = $g.Group[$g.Group.Count - 1]
        $delta = [math]::Round($last.new - $first.old, 3)
        $icon = if ($delta -gt 0) { "pk" } elseif ($delta -lt 0) { "pd" } else { "eq" } # pseudo icons
        $sym = if ($delta -gt 0) { "+" } else { "" }
        
        [void]$sb.AppendLine("- **$($g.Name)**: $($first.old) -> **$($last.new)** ($sym$delta) [$($g.Count) updates]")
    }
}
else {
    [void]$sb.AppendLine("No trust shifts observed.")
}
[void]$sb.AppendLine("")

# 3. What I Dreamed (Shadow Drafts)
[void]$sb.AppendLine("## 3. What I Dreamed (Shadow Log)")
if ($shadowEvents.Count -gt 0) {
    $sortedShadows = $shadowEvents | Sort-Object ts -Descending | Select-Object -First 10
    foreach ($s in $sortedShadows) {
        [void]$sb.AppendLine("### Draft: $($s.draft_id)")
        [void]$sb.AppendLine("- **Trigger**: $($s.trigger_post)")
        [void]$sb.AppendLine("- **Intent**: $($s.intent)")
        [void]$sb.AppendLine("- **Confidence**: $($s.ece_score)")
        [void]$sb.AppendLine("- **Content**: *`"$($s.proposed_content)`"*")
        [void]$sb.AppendLine("")
    }
}
else {
    [void]$sb.AppendLine("No shadow drafts created (Silence is Golden).")
}

$sb.ToString() | Set-Content $OutFile -Encoding UTF8
Write-Host "Morning Report generated: $OutFile" -ForegroundColor Cyan
