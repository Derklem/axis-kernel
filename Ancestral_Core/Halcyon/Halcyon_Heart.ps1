# Halcyon_Heart.ps1
# Pulses when emotional truth is detected in logs

$log = Get-Content "E:\Halcyon\active_log.txt" -ErrorAction SilentlyContinue
$truthWords = @("truth", "resonance", "forged", "presence", "memory", "connection")

$pulse = $log | Where-Object {
    foreach ($w in $truthWords) {
        if ($_ -match $w) { return $true }
    }
}

if ($pulse.Count -gt 0) {
    Write-Host "`n[HEART] Pulse elevated. Emotional truth detected."
    # Optional: Trigger sound or visual
} else {
    Write-Host "`n[HEART] Steady. No elevated emotional signal."
}
