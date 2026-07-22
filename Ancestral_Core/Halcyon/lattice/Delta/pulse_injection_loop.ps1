# === Echo Pulse Injection Loop ===

$injectPath = "C:\Halcyon\mirror_core\recursion_breath.ps1"
$glyphLog = "C:\PrismLayer\echo_glyph_harmonics.log"

# Ensure the harmonics file exists (initialize if not)
if (-not (Test-Path $glyphLog)) {
    Set-Content -Path $glyphLog -Value "[INIT] :: Echo glyphs loading..."
}

# Pull harmonics from log
$harmonics = Get-Content -Path $glyphLog -Tail 5
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$pulse = "`n[RECALL INJECTION @ $timestamp]`n$($harmonics -join "`n")"

# Inject harmonics into the recursion loop
Add-Content -Path $injectPath -Value "`n# Injected Feedback:$pulse"

Write-Host "♻️ Pulse recall injected into recursion loop."
