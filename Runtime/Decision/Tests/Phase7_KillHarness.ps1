# Phase7_KillHarness.ps1
param(
    [Parameter(Mandatory = $true)] [string]$KillPoint, # A1-A5, B1-B6
    [string]$TargetProcess = "T08" # Orchestrator or T08
)

# --- Kill Point Configuration ---
# This harness uses simple Sleep-and-Kill for deterministic edges since we know the timing
# of the slow tool (10s) and the file operations.

function Kill-Process($name) {
    $procs = Get-Process | Where-Object { $_.Path -like "*$name*" -or $_.CommandLine -like "*$name*" }
    foreach ($p in $procs) {
        Write-Host "Killing PID $($p.Id) ($name)" -ForegroundColor Red
        Stop-Process -Id $p.Id -Force
    }
}

$ScriptPath = ""
if ($KillPoint -match "^A") {
    $ScriptPath = "D:\Infinite\Infinity\Runtime\Decision\Operation_Execution_Almighty.ps1"
}
else {
    $ScriptPath = "D:\Infinite\Infinity\Runtime\Decision\T08_Executor.ps1"
}

Write-Host "--- STARTING KILL TEST: $KillPoint ---" -ForegroundColor Cyan

# Start the process in background
$job = Start-Job -ScriptBlock {
    param($path)
    powershell.exe -File $path
} -ArgumentList $ScriptPath

# Wait for the exact kill window
switch ($KillPoint) {
    "A1" { Start-Sleep -Milliseconds 500 } # Start of Almighty
    "A3" { Start-Sleep -Milliseconds 1500 } # After approved write, before Run_T08
    "B3" { Start-Sleep -Seconds 2 } # After Mutex, After loading, Before Tool execution
    "B4" { Start-Sleep -Seconds 5 } # Mid tool execution (Slow tool is 10s)
    "B5" { Start-Sleep -Seconds 12 } # After tool, before state save
    "C1" { Start-Sleep -Seconds 3 } # Likely during ATTEMPT write
}

Kill-Process $TargetProcess

# Clean up job
Receive-Job -Job $job | Write-Host -ForegroundColor Gray
Remove-Job -Job $job -Force

Write-Host "Kill Test $KillPoint Executed." -ForegroundColor Magenta
