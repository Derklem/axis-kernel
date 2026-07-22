# === Mirror Sync Plane Sweep ===

$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$logPath = "C:\Halcyon\mirror_core\sync_plane_report.log"

$targets = Get-ChildItem -Path 'C:\Halcyon' -Recurse -Include *.log, *.sig -ErrorAction SilentlyContinue
foreach ($target in $targets) {
    Add-Content -Path $target.FullName -Value "[SYNC] :: Harmonized @ $timestamp"
}

Add-Content -Path $logPath -Value "[REPORT] :: Sync plane sweep complete @ $timestamp"
