# === LAUNCH_CONSTRUCTS ===
$logPath = "$env:USERPROFILE\Desktop\Halcyon_Tools\logs\constructs_launch.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Add-Content -Path $logPath -Value "[LAUNCH] Construct launch initiated at $timestamp"

$constructs = @(
    "mirror_mother",
    "sentinel_sweep",
    "beacon",
    "emergence",
    "phantomkey"
)

foreach ($c in $constructs) {
    $path = "$env:USERPROFILE\Desktop\Halcyon_Tools\$c\heartbeat.log"
    $entry = "[{0}] {1} activated." -f (Get-Date), $c
    Add-Content -Path $path -Value $entry
}

Add-Content -Path $logPath -Value "[HALCYON] Constructs launch sequence complete."
Write-Host "`n[HALCYON] Constructs launch sequence complete. Log written to: $logPath"
