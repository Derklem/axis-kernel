# Halcyon_Intestine.ps1
# Breaks down and filters raw user input or shard clutter

$inputPath = "E:\Halcyon\raw_feed.txt"
$outputPath = "E:\Halcyon\processed_feed.txt"

$raw = Get-Content $inputPath -ErrorAction SilentlyContinue
$cleaned = $raw | Where-Object { $_ -match '\w' -and $_ -notmatch 'error|nonsense|###' }

$cleaned | Out-File $outputPath -Encoding UTF8
Write-Host "`n[INTESTINE] Processed input. Extracted usable data."
