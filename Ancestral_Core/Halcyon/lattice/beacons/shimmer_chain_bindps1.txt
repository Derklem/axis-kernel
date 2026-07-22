# === Shimmer Chain Bind ===
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
$pathRoot = "C:\Halcyon\lattice"
$files = Get-ChildItem $pathRoot -Recurse -File

$variance = $files.Count
$glyphPath = "C:\PrismLayer\shimmer_chain_bind.glyph"
Add-Content -Path $glyphPath -Value "`n[CHAIN_LINK_GLYPH @ $timestamp]"

foreach ($file in $files) {
    try {
        $hash = Get-FileHash -Path $file.FullName -Algorithm SHA256
        Add-Content -Path $glyphPath -Value "$($file.FullName) :: SHA256=$($hash.Hash)"
    } catch {
        Add-Content -Path $glyphPath -Value "[ERROR] $($file.FullName) :: $_"
    }
}

if ($variance -gt 100) {
    Add-Content -Path $glyphPath -Value "⚠️ High variance detected: $variance nodes"
}

Write-Host "🔗 Shimmer chain seeded. Chain-link glyph stored."
