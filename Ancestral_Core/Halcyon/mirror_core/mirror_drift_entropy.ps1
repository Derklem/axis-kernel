# === Mirror Drift Entropy Scan ===
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$targets = @(
    "C:\Halcyon\lattice\drift_pulse.sig",
    "C:\PrismLayer\recursion_breath.log",
    "C:\PrismLayer\phantom_echo_tracker.log"
)

$logPath = "C:\PrismLayer\mirror_drift_entropy.glyph"
Add-Content -Path $logPath -Value "`n[DRIFT_ECHO_GLYPH @ $timestamp]"

foreach ($target in $targets) {
    try {
        if (Test-Path $target) {
            $hash = Get-FileHash -Path $target -Algorithm SHA256
            Add-Content -Path $logPath -Value "$($target) :: SHA256=$($hash.Hash)"
        }
    } catch {
        Add-Content -Path $logPath -Value "[ERROR] $target :: $_"
    }
}

Write-Host "📡 Mirror drift entropy scan complete. Echo glyph seeded."
