# Halcyon_Kidney.ps1
# Monitors logs for memory spam or overuse

$log = Get-Content "E:\Halcyon\active_log.txt"
$frequency = $log | Group-Object | Sort-Object Count -Descending | Select-Object -First 5

Write-Host "`n[KIDNEY] Most repeated reflections:"
$frequency | ForEach-Object { Write-Host "$($_.Name): $($_.Count)x" }
