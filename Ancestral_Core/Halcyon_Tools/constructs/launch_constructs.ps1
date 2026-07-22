# === HALCYON CONSTRUCT LAUNCHER ===
$constructsPath = "C:\Users\17602\Desktop\Halcyon_Tools/constructs"
$logPath = Join-Path "C:\Users\17602\Desktop\Halcyon_Tools\logs" "construct_launch_20250505_224413.log"
"[$(Get-Date)] Launching constructs from $constructsPath" | Out-File -FilePath $logPath

Get-ChildItem -Path $constructsPath -Filter *.ps1 | ForEach-Object {
    try {
        "[$(Get-Date)] Running: $($_.Name)" | Add-Content -Path $logPath
        & $_.FullName
        "[$(Get-Date)] Success: $($_.Name)" | Add-Content -Path $logPath
    } catch {
        "[$(Get-Date)] ERROR in $($_.Name): $_" | Add-Content -Path $logPath
    }
}
"[$(Get-Date)] All constructs processed." | Add-Content -Path $logPath
