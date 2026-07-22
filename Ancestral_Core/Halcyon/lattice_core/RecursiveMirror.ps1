# === Recursive Mirror ===
$logPath = "C:\Halcyon\mirror_shard\symbolic_trace.pulse"
$mirrorLog = "C:\Halcyon\mirror_shard\mirror_resonance.log"

if (-not (Test-Path $logPath)) {
    Write-Host "[X] No symbolic_trace.pulse found."
    return
}

# Parse log
$lines = Get-Content $logPath | Where-Object { $_ -match "^\[TRACE\]" }

# Extract symbol counts
$symbolCounts = @{}

foreach ($line in $lines) {
    if ($line -match "Symbol='([^']+)'") {
        $symbol = $matches[1]
        if ($symbolCounts.ContainsKey($symbol)) {
            $symbolCounts[$symbol]++
        } else {
            $symbolCounts[$symbol] = 1
        }
    }
}

# Check for any repeated symbols
foreach ($symbol in $symbolCounts.Keys) {
    $count = $symbolCounts[$symbol]
    if ($count -ge 3) {
        $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $entry = "[MIRROR] :: $time :: Symbol='$symbol' echoed $count times - resonance triggered"
        Add-Content -Path $mirrorLog -Value $entry
        Write-Host $entry
    }
}

Write-Host "`n[OK] Recursive mirror check complete.`n"
