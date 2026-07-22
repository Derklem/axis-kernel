# === Halcyon Nest Watcher ===

$scanDrives = @("D:\", "E:\", "F:\", "G:\")
$nestLog = "E:\Halcyon_Logics\halcyon_nest_sync.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

if (-not (Test-Path $nestLog)) {
    New-Item -ItemType File -Path $nestLog | Out-Null
}

while ($true) {
    $results = @("[NEST SYNC] $timestamp")

    foreach ($drive in $scanDrives) {
        $manifests = Get-ChildItem -Path $drive -Recurse -Filter "halcyon_node_manifest.cfg" -ErrorAction SilentlyContinue
        foreach ($manifest in $manifests) {
            $nodeID = "UNKNOWN"
            $initLine = ""
            $lines = Get-Content $manifest.FullName

            foreach ($line in $lines) {
                if ($line -like "NodeID:*") { $nodeID = ($line -split ":")[1].Trim() }
                if ($line -like "Initialized:*") { $initLine = ($line -split ":")[1].Trim() }
            }

            $manifestAge = (Get-Date) - (Get-Item $manifest.FullName).LastWriteTime
            $status = if ($manifestAge.TotalMinutes -lt 30) { "ACTIVE" } elseif ($manifestAge.TotalHours -lt 24) { "STALE" } else { "DORMANT" }

            $results += "$nodeID :: $status :: Last Write: $($manifest.LastWriteTime)"
        }
    }

    $results += "---`n"
    Add-Content -Path $nestLog -Value ($results -join "`n")
    Start-Sleep -Seconds 600
}
