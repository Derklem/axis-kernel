# Run_ActuationCycle.ps1
# Phase 27.1: Deterministic Intake -> Actuation Wrapper
# Enforces ordering: Promoter runs first (stabilizes input), then Executor runs (actuates promoted).
# Phase 636: Executor call gated by Run_T08 authority wrapper.

param(
    [ValidateSet("intent_queue", "sandbox_queue")]
    [string]$QueueName = "intent_queue",
    [switch]$DryRun
)

$promoter = "D:\Infinite\Infinity\Runtime\Decision\Axis_Promoter.ps1"
$executorWrapper = "D:\Infinite\Infinity\Runtime\Decision\Run_T08.ps1"

$commonArgs = @("-QueueName", $QueueName)
if ($DryRun) { $commonArgs += "-DryRun" }

Write-Host "[CYCLE] Starting Promoter for $QueueName..." -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $promoter @commonArgs
if ($LASTEXITCODE -ne 0) {
    Write-Host "[CYCLE] Promoter Failed! Aborting Cycle." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "[CYCLE] Starting Executor Wrapper for $QueueName..." -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $executorWrapper @commonArgs
exit $LASTEXITCODE
