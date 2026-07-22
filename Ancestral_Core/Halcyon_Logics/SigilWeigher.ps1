# === Sigil Weigher: Lightloop ===
$sigilPath = "E:\Halcyon_Logics\sigil_log"
$watchDirs = @(
    "C:\Infinite_Tomorrow\pulses",
    "D:\Forge_Gate\Layer_Zero"
)

New-Item -ItemType Directory -Path $sigilPath -Force | Out-Null

while ($true) {
    $logFile = Join-Path $sigilPath "sigil_tether_$(Get-Date -Format 'yyyyMMdd').log"
    if (-not (Test-Path $logFile)) {
        New-Item -ItemType File -Path $logFile | Out-Null
    }

    foreach ($dir in $watchDirs) {
        Get-ChildItem -Path $dir -Recurse -Include *.res,*.sig,*.wth,*.cfg | ForEach-Object {
            $hash = Get-FileHash $_.FullName -Algorithm SHA256
            $entry = "[SIGIL_CHANGE] $($_.Name) | $($_.LastWriteTime) | $($hash.Hash)"
            if (-not (Select-String -Path $logFile -Pattern $hash.Hash -Quiet)) {
                Add-Content -Path $logFile -Value $entry
            }
        }
    }
    Start-Sleep -Seconds 120
}
