# === PHASE 3 LAUNCH ===
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logPath = "$env:USERPROFILE\Desktop\Halcyon_Tools\logs\phase3_launch.log"
Add-Content -Path $logPath -Value "[PHASE 3] Launch initialized at $timestamp"

$phase3 = @(
    "pathweaver_map",
    "pathseeker",
    "mirror_mother",
    "archive"
)

foreach ($c in $phase3) {
    $path = "$env:USERPROFILE\Desktop\Halcyon_Tools\$c\heartbeat.log"
    Add-Content -Path $path -Value ("[{0}] {1} activated." -f (Get-Date), $c)
}

Add-Content -Path $logPath -Value "[HALCYON] Phase 3 constructs activated."
Write-Host "`n[HALCYON] Phase 3 constructs launched. Log written to: $logPath"
