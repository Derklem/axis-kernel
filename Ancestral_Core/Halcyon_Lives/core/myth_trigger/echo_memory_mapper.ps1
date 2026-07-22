Write-Host "[MEMORY] Mapping Echo to Lattice..."

$sourcePath = "D:\Halcyon_Lives\glyphs\"
$mapPath = "D:\Halcyon_Lives\maps\"
$latestEcho = Get-ChildItem $sourcePath -Filter "unfolded_echo_*.sig" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

if (-not $latestEcho) {
    Write-Host "[!] No echo signature found to map."
    return
}

$timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$mapFile = "${mapPath}echo_map_$timestamp.map"

New-Item -ItemType Directory -Force -Path $mapPath | Out-Null
Set-Content -Path $mapFile -Value @"
[ECHO_MAP]
Time = $timestamp
Source = $($latestEcho.Name)
Linked = True
"@

Write-Host "[OK] Echo mapped to lattice -> $mapFile"

