<# 
.SYNOPSIS
  Axis Handler Dispatch (Phase 649-B)
.DESCRIPTION
  Maps intents -> handler scripts. Handlers must be read-only unless explicitly allowed.
#>

param(
    [Parameter(Mandatory = $true)] $Intent,
    [Parameter(Mandatory = $true)] $SystemMode
)

$ErrorActionPreference = "Stop"

$HandlersDir = "D:\Infinite\Infinity\Runtime\Decision\Handlers"
$task = $null

# Normalize “task” selector
if ($Intent.PSObject.Properties.Name -contains "task") { $task = [string]$Intent.task }
elseif ($Intent.PSObject.Properties.Name -contains "action") { $task = [string]$Intent.action }

if ([string]::IsNullOrWhiteSpace($task)) {
    return [ordered]@{ handled = $false; reason = "No task/action specified" }
}

$map = @{
    "system_diagnostic" = "H_SystemDiagnostic.ps1"
    "repair_memory"     = "H_RepairMemory.ps1"
    "kill_test"         = "H_KillTest.ps1"
}

if (-not $map.ContainsKey($task)) {
    return [ordered]@{ handled = $false; reason = ("No handler for task: {0}" -f $task) }
}

$handlerPath = Join-Path $HandlersDir $map[$task]
if (-not (Test-Path $handlerPath)) {
    return [ordered]@{ handled = $false; reason = ("Handler missing: {0}" -f $handlerPath) }
}

. $handlerPath
# Handler must expose: Invoke-AxisHandler
$result = Invoke-AxisHandler -Intent $Intent -SystemMode $SystemMode
return $result
