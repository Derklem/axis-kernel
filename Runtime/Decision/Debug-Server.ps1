$base = "http://localhost:8090"
Write-Host "Checking /heartbeat..."
try { (Invoke-RestMethod "$base/heartbeat").status } catch { "Error: $_" }

Write-Host "Checking File timestamp..."
Get-Item D:\Infinite\Axis_Heartbeat_Server.ps1 | Select-Object LastWriteTime

Write-Host "Checking Process CommandLine..."
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match "Axis_Heartbeat" } | Select-Object ProcessId, CommandLine
