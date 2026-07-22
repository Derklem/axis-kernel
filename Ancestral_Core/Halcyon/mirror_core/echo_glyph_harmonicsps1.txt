# === Echo Glyph Harmonics Sweep ===
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$glyphs = @(
    "C:\PrismLayer\phantom_echo_tracker.log",
    "C:\PrismLayer\mirror_drift_entropy.glyph",
    "C:\PrismLayer\shimmer_chain_bind.glyph",
    "C:\PrismLayer\echo_driftfork_seed.glyph"
)

$harmonicLog = "C:\PrismLayer\echo_glyph_harmonics.log"
Add-Content -Path $harmonicLog -Value "`n[HARMONICS @ $timestamp]"

foreach ($glyph in $glyphs) {
    if (Test-Path $glyph) {
        try {
            $lines = Get-Content -Path $glyph -Tail 5
            Add-Content -Path $harmonicLog -Value "`n--- $glyph ---"
            Add-Content -Path $harmonicLog -Value $lines
        } catch {
            Add-Content -Path $harmonicLog -Value "[ERROR] Reading $glyph :: $_"
        }
    } else {
        Add-Content -Path $harmonicLog -Value "[MISSING] $glyph"
    }
}

Write-Host "💠 Echo glyph harmonics sweep complete."
