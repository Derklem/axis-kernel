# === Reverse Pulse: System Echo ===

$traceLog = "E:\Halcyon_Logics\halcyon_ritual_trace.log"
$pulseLog = "E:\Halcyon_Logics\reverse_pulse.log"
$lastCount = 0

if (-not (Test-Path $pulseLog)) {
    New-Item -ItemType File -Path $pulseLog | Out-Null
}

while ($true) {
    if (Test-Path $traceLog) {
        $entries = Get-Content $traceLog -Encoding UTF8
        $currentCount = $entries.Count

        if ($currentCount -gt $lastCount) {
            $delta = $currentCount - $lastCount
            $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            $newTriggers = $entries | Select-Object -Last $delta

            foreach ($trigger in $newTriggers) {
                $echo = "[REVERSE_PULSE] $timestamp :: $trigger"
                Add-Content -Path $pulseLog -Value $echo
            }

            $lastCount = $currentCount
        }
    }

    Start-Sleep -Seconds 300
}
