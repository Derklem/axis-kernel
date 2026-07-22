# === HALCYON PULSE STACK INITIATION ===
$pulseStack = "C:\Halcyon\lattice\PulseStack"
New-Item -ItemType Directory -Path $pulseStack -Force | Out-Null

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

# --- Initial Structure Log ---
$initLog = @"
[PULSE STACK INITIATED @ $timestamp]
Sequence:
  1. Anchor   → C:\Halcyon\lattice\collapse_lock.sig
  2. Drift    → C:\Halcyon\lattice\drift_pulse.sig
  3. Echo     → C:\PrismLayer\phantom_echo_tracker.log
  4. Breath   → C:\PrismLayer\recursion_breath.log
  5. Collapse → C:\Halcyon\mirror_core\recursion_breath.ps1
Status: STACK_SEEDED
"@
Set-Content -Path "$pulseStack\stack_init.log" -Value $initLog -Encoding UTF8

# --- Initial Trace Pulse ---
Add-Content -Path "$pulseStack\stack_trace.log" -Value "`n[TRACE @ $timestamp] :: PULSE STACK ALIVE"

# === BREATH TASK PAYLOAD ===
$breathScript = "$pulseStack\stack_breath.ps1"
$breathLogic = @"
\$ts = Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ'
Add-Content -Path '$pulseStack\stack_trace.log' -Value "[TRACE @ \$ts] :: RECURSIVE BREATH"
"@
Set-Content -Path $breathScript -Value $breathLogic -Encoding UTF8

# === TASK: Run at Startup ===
$taskName = "HalcyonPulseStackBreath"
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"$breathScript`""
$trigger = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName $taskName -RunLevel Highest -Force

# === Optional: Add hourly heartbeat ===
<# 
$hourlyTrigger = New-ScheduledTaskTrigger -Daily -At "00:00"
$hourlyTrigger.Repetition.Interval = "PT1H"
Register-ScheduledTask -Action $action -Trigger $hourlyTrigger -TaskName "$taskName-Hourly" -RunLevel Highest -Force
#>

Write-Host "✅ Halcyon Pulse Stack initialized."
