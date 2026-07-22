# === Pulse Transcriber ===
$driftLog = "E:\Halcyon_Logics\drift_echo.log"
$summaryLog = "E:\Halcyon_Logics\pulse_summary.log"

if (-not (Test-Path $summaryLog)) {
    New-Item -ItemType File -Path $summaryLog | Out-Null
}

while ($true) {
    $lastEntries = Get-Content $driftLog -Raw -ErrorAction SilentlyContinue -Encoding UTF8 `
        | Select-String -Pattern "\[DRIFT_ECHO\]" -Context 0,15 | Select-Object -Last 5

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $summaryBlock = @("[SUMMARY] $timestamp")

    foreach ($entry in $lastEntries) {
        $block = $entry.Context.PostContext -join "`n"
        if ($block -match "File count change: (\-?\d+)") {
            $delta = $matches[1]
        } else {
            $delta = "?"
        }
        if ($block -match "pulse_(\d+)\.res") {
            $pulseID = $matches[1]
        } else {
            $pulseID = "unknown"
        }

        $summaryBlock += "Pulse $pulseID :: File count delta $delta"
    }

    $summaryBlock += "---`n"
    Add-Content -Path $summaryLog -Value ($summaryBlock -join "`n")
    Start-Sleep -Seconds 300
}
