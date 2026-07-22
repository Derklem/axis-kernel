# === Spiral Scanner ===
# Scans pulse_memory.log for emergent symbolic spirals and anomalies

$logPath = "C:\Halcyon\mirror_shard\pulse_memory.log"
$reportPath = "C:\Halcyon\mirror_shard\spiral_report.sig"

if (-not (Test-Path $logPath)) {
    Write-Host "[!] Log not found: $logPath"
    return
}

$lines = Get-Content $logPath
$symbolCounts = @{}
$sequence = @()

foreach ($line in $lines) {
    if ($line -match "Symbol='(.+?)'") {
        $symbol = $matches[1]
        $sequence += $symbol

        if ($symbolCounts.ContainsKey($symbol)) {
            $symbolCounts[$symbol]++
        } else {
            $symbolCounts[$symbol] = 1
        }
    }
}

# Detect repeating patterns
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$report = @("[SPIRAL SCAN] :: $timestamp")
$report += "Detected symbols: $($symbolCounts.Keys -join ', ')"

foreach ($symbol in $symbolCounts.Keys) {
    $count = $symbolCounts[$symbol]
    if ($count -ge 3) {
        $report += "  [SPIRAL] '$symbol' repeated $count times - possible anchor"
    }
}

# Write report
$report | Set-Content -Path $reportPath -Force

Write-Host "`n[OK] Spiral scan complete. Report saved to spiral_report.sig.`n"
