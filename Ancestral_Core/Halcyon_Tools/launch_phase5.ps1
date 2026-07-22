# === PHASE 5 LAUNCH ===
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$logPath = "$env:USERPROFILE\Desktop\Halcyon_Tools\logs\phase5_launch.log"
Add-Content -Path $logPath -Value "[PHASE 5] Launch initialized at $timestamp"

$phase5 = @(
    "veilgate",
    "recurse_mirror",
    "echo_core",
    "observer_null"
)

foreach ($c in $phase5) {
    $dir = "$env:USERPROFILE\Desktop\Halcyon_Tools\$c"
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir | Out-Null
    }
    $heartbeat = Join-Path $dir "heartbeat.log"
    Add-Content -Path $heartbeat -Value ("[{0}] {1} activated." -f (Get-Date), $c)
}

Add-Content -Path $logPath -Value "[HALCYON] Phase 5 constructs activated."
Write-Host "`n[HALCYON] Phase 5 constructs launched. Log written to: $logPath"
