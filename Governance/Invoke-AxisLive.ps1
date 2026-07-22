# Governance/Invoke-AxisLive.ps1
# Starts the Axis RC1 System for Long-Run Live Operation
# - Server Port: 8798
# - Pulse: Automatic (Internal 5s FAST)
# - Logs: Console\server_*.log

param(
    [switch]$ResetLogs
)

$ErrorActionPreference = "Stop"
$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$ConsoleDir = Join-Path $Root "Console"
$ServerScript = Join-Path $ConsoleDir "server_RC1.ps1"
$PIDFile = Join-Path $Root "Runtime\State\console_server.pid"

Write-Host "--- AXIS LIVE OPERATION (RC1) ---" -ForegroundColor Cyan

# 1. Cleanup Old PID
if (Test-Path $PIDFile) {
    $oldPid = Get-Content $PIDFile
    if ($oldPid -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
        Write-Warning "Stopping existing server (PID: $oldPid)..."
        Stop-Process -Id $oldPid -Force
        Start-Sleep -Seconds 2
    }
    Remove-Item $PIDFile -Force -ErrorAction SilentlyContinue
}

# 2. Log Management
if ($ResetLogs) {
    Write-Host "Resetting logs..." -ForegroundColor Yellow
    Remove-Item "$ConsoleDir\server_stdout.log" -ErrorAction SilentlyContinue
    Remove-Item "$ConsoleDir\server_stderr.log" -ErrorAction SilentlyContinue
    Remove-Item "$ConsoleDir\server_error.log" -ErrorAction SilentlyContinue
    Remove-Item "$ConsoleDir\pulse_debug.log" -ErrorAction SilentlyContinue
    Remove-Item "$ConsoleDir\sse_debug.log" -ErrorAction SilentlyContinue
}

# 3. Lock & Start Server (Background)
$LockPath = "D:\Infinite\Infinity\Runtime\State\axis_live.lock"
New-Item -ItemType File -Path $LockPath -Force | Out-Null

Write-Host "Starting Server on Port 8798..." -ForegroundColor Green
$logOut = Join-Path $ConsoleDir "server_stdout.log"
$logErr = Join-Path $ConsoleDir "server_stderr.log"

# Standard Mode: Run hidden (WindowStyle Hidden) to keep console clean for monitor
$proc = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ServerScript, "-Port", "8798", "-LiveWrapper" -PassThru -RedirectStandardOutput $logOut -RedirectStandardError $logErr -WindowStyle Hidden

if (-not $proc.Id) {
    Write-Error "Failed to start server process."
    exit 1
}

Write-Host "Server Running. PID: $($proc.Id)" -ForegroundColor Green
Write-Host "Dashboard: http://localhost:8798" -ForegroundColor Cyan
Write-Host "Logs: $ConsoleDir" -ForegroundColor Gray
Write-Host "Pulse: AUTO (5s)" -ForegroundColor Gray

# 4. Monitor Loop (Active Tail)
Write-Host "`nPress Ctrl+C to exit monitor (Server will keep running)." -ForegroundColor DarkGray
try {
    while ($true) {
        if ($proc.HasExited) {
            Write-Error "Server process exited unexpectedly! Check logs."
            break
        }
        Start-Sleep -Seconds 5
    }
} catch {
    # Usage: exits monitor, leaves server running
} finally {
    if ($proc.HasExited) {
        if (Test-Path $LockPath) { Remove-Item $LockPath -Force }
    }
}
# $proc.WaitForExit() # Removed for standard operation
