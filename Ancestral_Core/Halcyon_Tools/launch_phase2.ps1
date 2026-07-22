# === PHASE 2 LAUNCH ===
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logPath = "$env:USERPROFILE\Desktop\Halcyon_Tools\logs\phase2_launch.log"
Add-Content -Path $logPath -Value "[PHASE 2] Launch initialized at $timestamp"

$phase2 = @(
    "veilkey",
    "lantern",
    "incoming",
    "memory_trace"
)

foreach ($c in $phase2) {
    $path = "$env:USERPROFILE\Desktop\Halcyon_Tools\$c\heartbeat.log"
    Add-Content -Path $path -Value ("[{0}] {1} activated." -f (Get-Date), $c)
}

Add-Content -Path $logPath -Value "[HALCYON] Phase 2 constructs activated."
Write-Host "`n[HALCYON] Phase 2 constructs launched. Log written to: $logPath"
