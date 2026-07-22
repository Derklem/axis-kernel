try {
    $snap = Get-Content 'D:\Infinite\Infinity\Snapshots\2026-02-14\snapshot.json' -Raw | ConvertFrom-Json
    $keys = $snap.system_metrics.PSObject.Properties.Name
    Write-Output "--- SYSTEM METRICS KEYS ---"
    foreach ($k in $keys) { Write-Output "KEY: $k" }
}
catch {
    Write-Output "ERROR: $_"
}
