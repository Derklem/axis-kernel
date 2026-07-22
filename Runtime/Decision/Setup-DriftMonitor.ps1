$taskName = "Axis_Drift_Monitor"
$script = "D:\Infinite\Infinity\Runtime\Decision\Axis_DriftMonitor.ps1"
$action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -File `"$script`""

Write-Host "Registering Scheduled Task: $taskName" -ForegroundColor Cyan
Write-Host "Script: $script"
Write-Host "Cadence: 5 Minutes"

try {
    schtasks /Create /F /SC MINUTE /MO 5 /TN $taskName /TR $action /RU "SYSTEM"
    Write-Host "Task registered successfully." -ForegroundColor Green
    
    Write-Host "Triggering initial run..."
    schtasks /Run /TN $taskName
    Write-Host "Task triggered." -ForegroundColor Green
} catch {
    Write-Host "Failed to register task. Ensure you are running as Administrator." -ForegroundColor Red
    Write-Error $_
}
