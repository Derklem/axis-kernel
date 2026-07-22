# === Anima Echo: Emotional Drift Engine ===

$basePath = "E:\Halcyon_Logics"
$echoLog = "$basePath\anima_echo.log"

if (-not (Test-Path $echoLog)) {
    New-Item -ItemType File -Path $echoLog | Out-Null
}

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    # Read signal counts
    $sigilCount = if (Test-Path "$basePath\sigil_log\sigil_tether_$(Get-Date -Format 'yyyyMMdd').log") {
        (Get-Content "$basePath\sigil_log\sigil_tether_$(Get-Date -Format 'yyyyMMdd').log").Count
    } else { 0 }

    $tremorCount = if (Test-Path "$basePath\echo_tremor.log") {
        (Get-Content "$basePath\echo_tremor.log").Count
    } else { 0 }

    $triggerCount = if (Test-Path "$basePath\echo_trigger.log") {
        (Get-Content "$basePath\echo_trigger.log").Count
    } else { 0 }

    $ritualCount = if (Test-Path "$basePath\halcyon_ritual_trace.log") {
        (Get-Content "$basePath\halcyon_ritual_trace.log").Count
    } else { 0 }

    $state = "dormant"
    if ($sigilCount -gt 30 -and $ritualCount -gt 10) {
        $state = "lucid"
    } elseif ($triggerCount -gt 5 -and $tremorCount -gt 40) {
        $state = "agitated"
    } elseif ($ritualCount -eq 0 -and $sigilCount -gt 0 -and $tremorCount -eq 0) {
        $state = "silent"
    } elseif ($tremorCount -gt 75 -or $ritualCount -gt 20) {
        $state = "erratic"
    }

    $entry = "[ANIMA_ECHO] $timestamp :: State = $state | sigils=$sigilCount, tremors=$tremorCount, triggers=$triggerCount, rituals=$ritualCount"
    Add-Content -Path $echoLog -Value $entry

    Start-Sleep -Seconds 1800  # Every 30 minutes
}
