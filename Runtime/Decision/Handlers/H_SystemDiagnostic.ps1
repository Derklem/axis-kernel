function Invoke-AxisHandler {
    param(
        [Parameter(Mandatory = $true)] $Intent,
        [Parameter(Mandatory = $true)] $SystemMode
    )

    $ErrorActionPreference = "Stop"

    # Enforce read-only posture (don’t rely on caller)
    if ($SystemMode.mode -ne "OBSERVATION_ONLY") {
        return [ordered]@{
            handled = $true; task = "system_diagnostic"; handler = "H_SystemDiagnostic.ps1"
            status = "BLOCKED"; output = @{ reason = "SystemMode not OBSERVATION_ONLY" }
        }
    }

    $Root = "D:\Infinite\Infinity"
    $Runtime = Join-Path $Root "Runtime\Decision"

    $files = @{
        drift_heartbeat = (Join-Path $Runtime "drift_heartbeat.jsonl")
        decision_log    = (Join-Path $Runtime "decision_log.jsonl")
        review_log      = (Join-Path $Runtime "Review\review_log.jsonl")
        voice_props     = (Join-Path $Runtime "Voice\voice_proposals.jsonl")
    }

    $summary = [ordered]@{
        ts_utc = (Get-Date).ToUniversalTime().ToString("o")
        mode   = $SystemMode.mode
        counts = @{}
        tails  = @{}
    }

    foreach ($k in $files.Keys) {
        $p = $files[$k]
        if (Test-Path $p) {
            $summary.counts[$k] = (Get-Content $p | Measure-Object).Count
            $summary.tails[$k] = @(Get-Content $p -Tail 2)
        }
        else {
            $summary.counts[$k] = 0
            $summary.tails[$k] = @()
        }
    }

    return [ordered]@{
        handled = $true
        task    = "system_diagnostic"
        handler = "H_SystemDiagnostic.ps1"
        status  = "OK"
        output  = $summary
    }
}
