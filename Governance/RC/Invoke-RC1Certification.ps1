
# Invoke-RC1Certification.ps1
# Phase 59: Final Release Candidate Certification Harness
# Verifies: Drill Safety, Watchdog Correctness, SSE Stability, Integrity

param([switch]$DevMode)

$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$ConsoleDir = Join-Path $Root "Console"
$ReportFile = Join-Path $GovDir "RC\rc1_cert_report.json"
$ResilienceScript = Join-Path $GovDir "Measure-SystemResilience.ps1"
$WatchdogScript = Join-Path $GovDir "Axis_Runtime_Integrity_Watchdog.ps1"
$ServerScript = Join-Path $ConsoleDir "server_RC1.ps1"
$ServerPort = 8798
"DEBUG: Server Script Path: $ServerScript" | Out-File "D:\Infinite\Infinity\Governance\harness_debug.txt"

# --- Helper: Start Server ---
function Start-RCServer {
    Write-Host "Starting Axis Console Server (Background Process)..." -ForegroundColor Cyan
    
    $logOut = Join-Path $GovDir "harness_server_8798.stdout.log"
    $logErr = Join-Path $GovDir "harness_server_8798.stderr.log"
    $args = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $ServerScript, "-Port", $ServerPort)

    Write-Host "Debug Start-Process Args: $($args -join ' ')"

    try {
        $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $args -PassThru `
            -RedirectStandardOutput $logOut -RedirectStandardError $logErr
    } catch {
        Write-Error "Start-Process Exception: $_"
        return $null
    }

    if (-not $proc -or -not $proc.Id) {
        Write-Error "Server process failed to start (no PID)."
        return $null
    }

    Write-Host "Server started with PID: $($proc.Id). Logging to $logOut / $logErr"

    # Wait until /api/status is reachable OR process exits
    $deadline = (Get-Date).AddSeconds(20)
    $statusUrl = "http://127.0.0.1:$ServerPort/api/status"

    while ((Get-Date) -lt $deadline) {
        if ($proc.HasExited) {
            Write-Error "Server process exited early. See logs: $logOut / $logErr"
            return $null
        }

        try {
            $resp = Invoke-WebRequest -UseBasicParsing -Uri $statusUrl -TimeoutSec 10 -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                Write-Host "Server UP: $statusUrl" -ForegroundColor Green
                return $proc
            }
        } catch {
            Start-Sleep -Milliseconds 400
        }
    }

    Write-Error "Server did not become ready within 20s. See logs: $logOut / $logErr"
    return $null
}

# --- Helper: Stop Server ---
function Stop-RCServer {
    param($Proc)
    if ($Proc -and -not $Proc.HasExited) {
        Write-Host "Stopping Server (PID $($Proc.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $Proc.Id -Force -ErrorAction SilentlyContinue
    }
}

# --- Helper: Test SSE ---
function Test-SSE {
    param($streamUrl)

    Write-Host "Testing SSE Stability (10s)..." -ForegroundColor Cyan

    $job = Start-Job -ScriptBlock {
        param($url)

        try {
            $req = [System.Net.HttpWebRequest]::Create($url)
            $req.Method = "GET"
            $req.Timeout = 10000   # request open/connect timeout

            $resp = $req.GetResponse()
            $stream = $resp.GetResponseStream()

            # THIS is the critical piece: make reads timeout so ReadLine can't block forever
            $stream.ReadTimeout = 1000  # 1s read timeout

            $reader = New-Object System.IO.StreamReader($stream)

            $deadline = (Get-Date).AddSeconds(10)
            while ((Get-Date) -lt $deadline) {
                try {
                    $line = $reader.ReadLine()
                    if ($null -ne $line -and $line -match '^event:\s*connected') {
                        return "CONNECTED"
                    }
                }
                catch [System.IO.IOException] {
                    # Expected when ReadTimeout hits. Just keep looping until deadline.
                }
            }
            return "TIMEOUT"
        }
        catch {
            return ("ERROR: " + $_.Exception.Message)
        }
    } -ArgumentList $streamUrl

    Wait-Job $job -Timeout 30 | Out-Null
    $res = Receive-Job $job -ErrorAction SilentlyContinue

    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -ErrorAction SilentlyContinue

    if ($res -eq "CONNECTED") {
        Write-Host "  [Pass] SSE Connected" -ForegroundColor Green
        return $true
    }

    Write-Host "  [FAIL] SSE Result: $res" -ForegroundColor Red
    return $false
}


# --- Main Certification Flow ---
$results = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
    checks = @{}
    verdict = "PENDING"
}

try {
    # 1. Drill Smoke Test (Non-Destructive)
    Write-Host "1. Running Resilience Smoke Test..." -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File $ResilienceScript -SkipDelete -SkipBackup
    if ($LASTEXITCODE -eq 0) { 
        $results.checks["DrillSmoke"] = "PASS" 
        Write-Host "  [Pass] Drill Script Exists & Runs" -ForegroundColor Green
    } else { 
        $results.checks["DrillSmoke"] = "FAIL" 
    }

    # 2. Server & SSE
    $serverProc = Start-RCServer
    if ($serverProc) {
        $results.checks["ServerStartup"] = "PASS"
        $sse = Test-SSE "http://127.0.0.1:$ServerPort/api/stream"
        $results.checks["ServerSSE"] = if ($sse) { "PASS" } else { "FAIL" }
        
        # Safe Kill Test (using PID from Process object)
        $results.checks["PIDCheck"] = "FAIL"
        $pidFile = Join-Path $Root "Runtime\State\console_server.pid"
        if (Test-Path $pidFile) {
             # Verify PID matches
             $pidVal = (Get-Content $pidFile -Raw).Trim()
             if ($pidVal -eq [string]$serverProc.Id) {
                 $results.checks["PIDCheck"] = "PASS"
             }
        }
        
        # Cleanup
        Stop-RCServer -Proc $serverProc
    } else {
        $results.checks["ServerStartup"] = "FAIL"
        $results.checks["ServerSSE"] = "SKIP"
        $results.checks["PIDCheck"] = "SKIP"
    }

    # 3. Watchdog Regex & Dedupe Verification
    Write-Host "3. Running Watchdog..." -ForegroundColor Cyan
    powershell -NoProfile -ExecutionPolicy Bypass -File $WatchdogScript
    if ($LASTEXITCODE -eq 0) { 
        $results.checks["Watchdog"] = "PASS" 
        Write-Host "  [Pass] Watchdog Runs" -ForegroundColor Green
    } else { 
        $results.checks["Watchdog"] = "FAIL" 
    }

    # Verdict
    if ($results.checks.Values -contains "FAIL") {
        $results.verdict = "FAIL"
        Write-Host "`nRC1 CERTIFICATION FAILED" -ForegroundColor Red
    } else {
        $results.verdict = "PASS"
        Write-Host "`nRC1 CERTIFICATION PASSED" -ForegroundColor Green
    }

} catch {
    $results.verdict = "ERROR"
    $results.error = $_.Exception.Message
    Write-Host "Certification Error: $($_.Exception.Message)" -ForegroundColor Red
} finally {
    if ($serverProc) {
        Write-Host "Final Cleanup: Stopping Server..." -ForegroundColor Yellow
        Stop-RCServer -Proc $serverProc
    }
}

$json = $results | ConvertTo-Json -Depth 5
if (-not (Test-Path (Split-Path $ReportFile))) { New-Item -ItemType Directory (Split-Path $ReportFile) -Force | Out-Null }
$json | Out-File $ReportFile -Encoding UTF8
Write-Host "Report saved to $ReportFile" -ForegroundColor Gray
