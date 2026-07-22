param([switch]$DryRun)
$RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$ModeFile = Join-Path $RuntimeDir "system_mode.json"
if (Test-Path $ModeFile) {
    $global:SystemMode = Get-Content $ModeFile | ConvertFrom-Json
} else {
    $global:SystemMode = @{ mode = "OBSERVATION_ONLY" }
}
$ExecutorBuild = "TEST"
$DecLog = Join-Path $RuntimeDir "decision_log_test.jsonl"
$LogPolicyHelper = Join-Path $RuntimeDir "T08_DecisionLogPolicy.ps1"
if (Test-Path $LogPolicyHelper) { . $LogPolicyHelper }

function Append-DecLog($msg, $intentId, $result) {
    if ($global:LogPolicyActive) {
        $mode = if ($global:SystemMode.mode) { $global:SystemMode.mode } else { "OBSERVATION_ONLY" }
        if (-not (Test-ShouldEmitLog -Mode $mode -ResultCode $result)) {
            Write-Host "[Suppressed] $result"
            return
        }
    }
    Write-Host "[EMITTED] $result: $msg"
}

Append-DecLog "Test suppression" "SYS" "HEARTBEAT"
Append-DecLog "Test emission" "SYS" "EXEC_SUCCESS"
