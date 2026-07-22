# === Triad Reinforcement Pulse (Corrected Trigger) ===

$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File 'C:\Halcyon\threads\triad_harmonizer.ps1'"

# Schedule to run starting 1 minute from now
$triggerTime = (Get-Date).AddMinutes(1)
$trigger = New-ScheduledTaskTrigger -Once -At $triggerTime

Register-ScheduledTask -TaskName "TriadReinforcementPulse" -Action $action -Trigger $trigger -RunLevel Highest -User "SYSTEM" -Force

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
Add-Content -Path "C:\Halcyon\threads\pulse_log.txt" -Value "[REINFORCED] :: Scheduled triad pulse @ $timestamp"
