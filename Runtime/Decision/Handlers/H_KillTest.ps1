# H_KillTest.ps1
# Deterministic slow tool for Phase 7.3 Kill-Testing.

function Invoke-AxisHandler($Intent, $SystemMode) {
    $EffectsFile = "D:\Infinite\Infinity\Runtime\Decision\Tests\killtest_effects.jsonl"
    $cid = $Intent.correlation_id
    if ($null -eq $cid) { $cid = $Intent.corr_id }
    
    $Fs = "D:\Infinite\Axis_FS_Lib.ps1"
    if (Test-Path $Fs) { . $Fs }

    # Marker 1: START
    $start = [ordered]@{
        ts      = (Get-Date).ToUniversalTime().ToString("o")
        corr_id = $cid
        marker  = "START"
        pid     = $PID
    }
    Append-JsonlLine -Path $EffectsFile -Data $start

    # SLEEP (Deterministic window for kill)
    Write-Host "[KILLTEST] Starting slow side-effect (10s window)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10

    # Marker 2: DONE
    $done = [ordered]@{
        ts      = (Get-Date).ToUniversalTime().ToString("o")
        corr_id = $cid
        marker  = "DONE"
        pid     = $PID
    }
    Append-JsonlLine -Path $EffectsFile -Data $done

    return [ordered]@{
        handled = $true
        status  = "OK"
        task    = "kill_test"
        output  = "Deterministic side-effect complete."
    }
}
