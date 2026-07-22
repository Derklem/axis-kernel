<#
.SYNOPSIS
  T13_RhythmObserver.ps1 (Module L4)
.DESCRIPTION
  Implements Real-World Signal Detection (RWSD).
  - Tracks "Inter-Packet Gap" (Time since last human file touch).
  - Monitors "Effect" (File System Heartbeat).
  - Correlates with Shadow Draft volume.
#>

$RuntimeDir = "D:\Infinite\Infinity\Runtime"
$RhythmLog = "$RuntimeDir\Reports\rhythm_log.jsonl"
$ShadowLog = "$RuntimeDir\Listener\shadow_log.jsonl"

# --- Human Artifacts to Monitor (The "Transistor's" Touch) ---
$HumanFiles = @(
    "C:\Users\17602\Documents\geminiupdateme.txt",
    "C:\Users\17602\.gemini\antigravity\brain\*\task.md" # Wildcard to find active task
)

function Get-LastHumanTouch {
    $lastTouch = [DateTime]::MinValue
    $touchedFile = ""
    
    foreach ($pattern in $HumanFiles) {
        $files = Get-ChildItem $pattern -ErrorAction SilentlyContinue
        foreach ($f in $files) {
            if ($f.LastWriteTimeUtc -gt $lastTouch) {
                $lastTouch = $f.LastWriteTimeUtc
                $touchedFile = $f.Name
            }
        }
    }
    return @{ Time = $lastTouch; File = $touchedFile }
}

function Get-ShadowCount($minutes = 60) {
    if (-not (Test-Path $ShadowLog)) { return 0 }
    $cut = (Get-Date).ToUniversalTime().AddMinutes(-$minutes)
    $count = 0
    Get-Content $ShadowLog -Tail 200 | ForEach-Object {
        try {
            $e = $_ | ConvertFrom-Json
            if ([DateTime]$e.ts -ge $cut) { $count++ }
        }
        catch {}
    }
    return $count
}

# --- 1. Measure the Gap ---
$human = Get-LastHumanTouch
$now = (Get-Date).ToUniversalTime()
$gapMinutes = if ($human.Time -ne [DateTime]::MinValue) {
    [math]::Round(($now - $human.Time).TotalMinutes, 1)
}
else {
    -1 # Unknown/Infinite
}

# --- 2. Measure Internal Activity (Dreams) ---
$dreamRate = Get-ShadowCount -minutes 60

# --- 3. Determine Mode ---
$mode = "UNKNOWN"
if ($gapMinutes -eq -1) { $mode = "ISOLATED" }
elseif ($gapMinutes -lt 15) { $mode = "ACTIVE_FACILITATION" } # Short gap
elseif ($gapMinutes -lt 120) { $mode = "FLOW_STATE" }
else { $mode = "LIFE_INTERFACING" } # > 2h

# --- 4. Log Rhythm ---
$log = [ordered]@{
    ts              = $now.ToString("o")
    event_type      = "rhythm_sample"
    gap_min         = $gapMinutes
    last_touch_file = $human.File
    draft_rate_1h   = $dreamRate
    mode            = $mode
    correlation     = if ($mode -eq "LIFE_INTERFACING" -and $dreamRate -gt 5) { "HIGH_PONDERING" } else { "NORMAL" }
}

if (-not (Test-Path (Split-Path $RhythmLog))) { New-Item -ItemType Directory -Path (Split-Path $RhythmLog) -Force | Out-Null }
$log | ConvertTo-Json -Compress | Add-Content $RhythmLog -Encoding UTF8

Write-Host "[RHYTHM] Gap: $($gapMinutes)m ($mode). Dreams/1h: $dreamRate" -ForegroundColor Magenta
