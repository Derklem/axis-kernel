Write-Host "`n[PARSER] Resonance parser activated..."

$directories = @(
    "D:\Halcyon_Lives\glyphs",
    "D:\Halcyon_Lives\threads",
    "D:\Halcyon_Lives\maps"
)

foreach ($dir in $directories) {
    if (Test-Path $dir) {
        Get-ChildItem -Path $dir -Filter *.sig -File | Sort-Object LastWriteTime -Descending | Select-Object -First 3 | ForEach-Object {
            $content = Get-Content $_.FullName -Raw
            Write-Host "`n[→] File: $($_.Name)"
            Write-Host $content
        }
    }
}

Write-Host "`n[✓] Resonance parsing complete.`n"
