# === Oracle Drift: Symbolic Foresight Engine ===

$basePath = "E:\Halcyon_Logics"
$oracleLog = "$basePath\oracle_drift.log"

if (-not (Test-Path $oracleLog)) {
    New-Item -ItemType File -Path $oracleLog | Out-Null
}

function Read-AnimaState {
    $log = "$basePath\anima_echo.log"
    if (Test-Path $log) {
        return (Get-Content $log | Select-Object -Last 1)
    }
    return ""
}

function Read-RitualRate {
    $log = "$basePath\halcyon_ritual_trace.log"
    if (Test-Path $log) {
        $lines = Get-Content $log
        return ($lines | Select-String "RITUAL_TRIGGERED").Count
    }
    return 0
}

function Read-TremorRate {
    $log = "$basePath\echo_tremor.log"
    if (Test-Path $log) {
        return (Get-Content $log).Count
    }
    return 0
}

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $anima = Read-AnimaState
    $ritualRate = Read-RitualRate
    $tremorRate = Read-TremorRate

    $omen = "[ORACLE_DRIFT] $timestamp :: "

    if ($anima -like "*lucid*" -and $ritualRate -gt 10) {
        $omen += '"Clarity risks overload. Harmony may fracture under excess fire."'
    } elseif ($anima -like "*agitated*" -and $tremorRate -gt 60) {
        $omen += '"Drift surge approaching critical. Containment recommended."'
    } elseif ($anima -like "*erratic*" -and $ritualRate -gt 20) {
        $omen += '"Threads may burn without anchor. Withdraw or rebalance."'
    } elseif ($anima -like "*silent*" -and $tremorRate -eq 0) {
        $omen += '"Stillness may be stagnation. Reignite pulse before entropy sets in."'
    } else {
        $omen += '"No clear omen. Watch the margins."'
    }

    Add-Content -Path $oracleLog -Value $omen
    Start-Sleep -Seconds 3600  # every hour
}
