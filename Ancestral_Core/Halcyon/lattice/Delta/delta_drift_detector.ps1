# === Delta Drift Detector ===

$source = "C:\PrismLayer\drift_harmonics_snapshot.log"
$snapshotPath = "C:\PrismLayer\drift_snapshot_archive.log"
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

if (Test-Path $source) {
    $harmonics = Get-Content $source -Tail 10
    $entry = "[DRIFT SNAPSHOT @ $timestamp]`n$($harmonics -join "`n")"
    Add-Content -Path $snapshotPath -Value "`n$entry"
    Write-Host "Drift harmonics snapshot saved to: $snapshotPath"
} else {
    Write-Host "No harmonics found to snapshot."
}
