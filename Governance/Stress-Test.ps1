# Governance/Stress-Test.ps1
# Phase 60: Controlled Load Probe for Kernel Validation
# Usage: .\Stress-Test.ps1 -Count 500 -SleepMs 100

param(
    [int]$Count = 500,
    [int]$SleepMs = 100
)

Write-Host "--- AXIS KERNEL STRESS TEST (PID: $((Get-Process -Id (Get-Content D:\Infinite\Infinity\Runtime\State\console_server.pid)).Id)) ---" -ForegroundColor Cyan
Write-Host "Target: http://localhost:8798"
Write-Host "Probes: $Count x (Status + Pulses)"

$sw = [System.Diagnostics.Stopwatch]::StartNew()

1..$Count | ForEach-Object {
    if ($_ % 50 -eq 0) { Write-Host "Probe $_ / $Count..." -NoNewline; Write-Host " $([math]::Round($sw.Elapsed.TotalSeconds, 1))s" -ForegroundColor Gray }
    
    try {
        # 1. Status (Lightweight)
        Invoke-WebRequest "http://localhost:8798/api/status" -UseBasicParsing -TimeoutSec 2 | Out-Null
        
        # 2. Pulses (Heavier JSON serialization)
        Invoke-WebRequest "http://localhost:8798/api/pulses?count=50" -UseBasicParsing -TimeoutSec 2 | Out-Null
        
        # 3. Econ (Ledger read)
        if ($_ % 10 -eq 0) {
            Invoke-WebRequest "http://localhost:8798/api/econ/status" -UseBasicParsing -TimeoutSec 2 | Out-Null
        }
    } catch {
        Write-Host "`n[FAIL] Probe $_ failed: $_" -ForegroundColor Red
    }
    
    Start-Sleep -Milliseconds $SleepMs
}

$sw.Stop()
Write-Host "`n--- TEST COMPLETE ---" -ForegroundColor Green
Write-Host "Duration: $([math]::Round($sw.Elapsed.TotalSeconds, 2))s"
Write-Host "Check telemetry usage for memory/handle spikes." -ForegroundColor Yellow
