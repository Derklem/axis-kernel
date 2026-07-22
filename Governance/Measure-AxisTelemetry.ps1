# Governance/Measure-AxisTelemetry.ps1
# Samples system health metrics for Long-Run Validation (Phase 60)
# - Run alongside Invoke-AxisLive.ps1
# - Output: Governance\telemetry_report.jsonl

param(
    [int]$IntervalSeconds = 60,
    [int]$DurationHours = 72
)

$ErrorActionPreference = "Stop"
$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$ConsoleDir = Join-Path $Root "Console"
$ReportFile = Join-Path $GovDir "telemetry_report.jsonl"
$PidFile = Join-Path $Root "Runtime\State\console_server.pid"

$PulseLedger = Join-Path $GovDir "integrity_pulse_ledger.jsonl"
$ErrorLog = Join-Path $ConsoleDir "server_error.log"

Write-Host "--- AXIS TELEMETRY SAMPLER (ENHANCED) ---" -ForegroundColor Cyan
Write-Host "Output: $ReportFile"
Write-Host "Interval: ${IntervalSeconds}s | Duration: ${DurationHours}h"

$startTime = Get-Date
$endTime = $startTime.AddHours($DurationHours)

# State tracking for drift
$prevWS = $null
$prevHandles = $null

while ((Get-Date) -lt $endTime) {
    try {
        $ts = (Get-Date).ToUniversalTime().ToString("o")
        
        # 1. Server Process Metrics
        $proc = $null
        $wsMB = 0
        $handles = 0
        $wsDelta = 0
        $handleDelta = 0
        
        if (Test-Path $PidFile) {
            $id = Get-Content $PidFile
            $proc = Get-Process -Id $id -ErrorAction SilentlyContinue
            if ($proc) {
                $wsMB = [math]::Round($proc.WorkingSet / 1MB, 2)
                $handles = $proc.HandleCount
                
                if ($prevWS -ne $null) { $wsDelta = [math]::Round($wsMB - $prevWS, 2) }
                if ($prevHandles -ne $null) { $handleDelta = $handles - $prevHandles }
                
                $prevWS = $wsMB
                $prevHandles = $handles
            }
        }

        # 2. Pulse Ledger Metrics & Integrity
        $pulseSize = 0
        $pulseAgeSec = -1
        $pulseValid = $true
        
        if (Test-Path $PulseLedger) {
            $item = Get-Item $PulseLedger
            $pulseSize = $item.Length
            
            # Age check
            $pulseAgeSec = [math]::Round((Get-Date).ToUniversalTime().Subtract($item.LastWriteTimeUtc).TotalSeconds, 1)
            
            # Integrity check (Tail decode)
            try {
                $tail = Get-Content $PulseLedger -Tail 1 -ErrorAction Stop
                if ($tail) {
                    $null = $tail | ConvertFrom-Json -ErrorAction Stop
                }
            } catch {
                $pulseValid = $false
            }
        }

        # 3. Error Log Size
        $errSize = 0
        if (Test-Path $ErrorLog) {
            $errSize = (Get-Item $ErrorLog).Length
        }

        # 4. Record
        $metric = [ordered]@{
            ts = $ts
            server_pid = if ($proc) { $proc.Id } else { $null }
            ws_mb = $wsMB
            ws_delta_mb = $wsDelta
            handles = $handles
            handle_delta = $handleDelta
            pulse_ledger_bytes = $pulseSize
            pulse_age_sec = $pulseAgeSec
            pulse_valid = $pulseValid
            error_log_bytes = $errSize
        }

        $json = $metric | ConvertTo-Json -Compress
        Add-Content -Path $ReportFile -Value $json
        
        # Console Feedback & Alerting
        $statusColor = "Green"
        $alerts = @()
        
        if (-not $proc) { $statusColor = "Red"; $alerts += "NO_PROC" }
        elseif ($pulseAgeSec -gt 20) { $statusColor = "Red"; $alerts += "LAG:${pulseAgeSec}s" }
        elseif (-not $pulseValid) { $statusColor = "Red"; $alerts += "CORRUPT" }
        elseif ($errSize -gt 0) { $statusColor = "Yellow"; $alerts += "ERR_LOG($errSize)" }
        elseif ($wsDelta -gt 5) { $statusColor = "Yellow"; $alerts += "MEM_SPIKE($wsDelta)" }
        
        $deltaStr = if ($wsDelta -ge 0) { "+$wsDelta" } else { "$wsDelta" }
        $hDeltaStr = if ($handleDelta -ge 0) { "+$handleDelta" } else { "$handleDelta" }
        
        $alertStr = ""
        if ($alerts) { $alertStr = " | [" + ($alerts -join ", ") + "]" }
        
        Write-Host "[$ts] PID:$($metric.server_pid) MEM:${wsMB}MB($deltaStr) HND:$handles($hDeltaStr) AGE:${pulseAgeSec}s$alertStr" -ForegroundColor $statusColor
        
    } catch {
        Write-Warning "Telemetry glitch: $_"
    }
    
    Start-Sleep -Seconds $IntervalSeconds
}

Write-Host "Telemetry Run Complete." -ForegroundColor Green
