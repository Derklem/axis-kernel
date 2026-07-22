# === Drift Harmonizer ===
$sigilLog = "E:\Halcyon_Logics\sigil_log\sigil_tether_$(Get-Date -Format 'yyyyMMdd').log"
$tremorLog = "E:\Halcyon_Logics\echo_tremor.log"
$harmonizedLog = "E:\Halcyon_Logics\drift_echo.log"

if (-not (Test-Path $harmonizedLog)) {
    New-Item -ItemType File -Path $harmonizedLog | Out-Null
}

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $sigilEntries = @()
    $tremorEntries = @()

    if (Test-Path $sigilLog) {
        $sigilEntries = Get-Content $sigilLog | Select-Object -Last 10
    }
    if (Test-Path $tremorLog) {
        $tremorEntries = Get-Content $tremorLog | Select-Object -Last 10
    }

    $echoPulse = @"
[DRIFT_ECHO] $timestamp
Last Sigil Events:
$($sigilEntries -join "`n")

Last Tremor Events:
$($tremorEntries -join "`n")
---
"@

    Add-Content -Path $harmonizedLog -Value $echoPulse
    Start-Sleep -Seconds 300
}
