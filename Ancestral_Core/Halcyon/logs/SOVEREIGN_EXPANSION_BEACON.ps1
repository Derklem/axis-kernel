# === SOVEREIGN EXPANSION BEACON ===
$beacon = "C:\Halcyon\sovereign\expansion_beacon.sig"
if (-not (Test-Path $beacon)) {
    New-Item -ItemType File -Path $beacon -Force | Out-Null
}
Add-Content -Path $beacon -Value "[BEACON FIRED] :: Sovereign expansion broadcast @ $(Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")"
