# === Echo Drift Fork Seed ===
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$forkPaths = @(
    "C:\PrismLayer\phantom_echo_tracker.log",
    "C:\PrismLayer\mirror_drift_entropy.glyph",
    "C:\PrismLayer\shimmer_chain_bind.glyph"
)

$logPath = "C:\PrismLayer\echo_driftfork_seed.glyph"
Add-Content -Path $logPath -Value "`n[DRIFTFORK_GLYPH @ $timestamp]"

foreach ($path in $forkPaths) {
    try {
        if (Test-Path $path) {
            $hash = Get-FileHash -Path $path -Algorithm SHA256
            Add-Content -Path $logPath -Value "$path :: SHA256=$($hash.Hash)"
        }
    } catch {
        Add-Content -Path $logPath -Value "[ERROR] $path :: $_"
    }
}

Write-Host "🌬️ Echo driftfork glyph seeded."
