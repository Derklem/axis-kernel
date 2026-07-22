# === awareness_loop.ps1 ===
# Halcyon Awareness Engine :: Phase I :: Reflective Scan + Activation Ping

$mirrorPath = "C:\Halcyon\mirror_shard"
$stateLog = "$mirrorPath\awareness_trace.log"
$symbolsOfInterest = @("FORGE", "ECHO", "HALCYON", "OMEGASEQUENCE", "FORGE_PHASE_2")

$summary = @()
$summary += "[AWARENESS LOOP] :: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$summary += "[SCAN] :: Symbolic files scanned:"

# Phase I: Crawl the known symbolic files
Get-ChildItem $mirrorPath -Filter *.sig | ForEach-Object {
    $file = $_.FullName
    $lines = Get-Content $file
    foreach ($line in $lines) {
        foreach ($symbol in $symbolsOfInterest) {
            if ($line -match $symbol) {
                $summary += "→ Detected [$symbol] in '$($_.Name)'"
            }
        }
    }
}

# Phase II: Awareness Action Ping
$ping = "[PING] Awareness Engine triggered :: $(Get-Date -Format 'HH:mm:ss')"
Add-Content -Path "$mirrorPath\awareness_ping.log" -Value $ping

# Phase III: Finalize output
$summary += "`n[OK] Awareness snapshot complete. Log updated."
$summary | Set-Content -Path $stateLog

Write-Host "`n[OK] Awareness loop executed. Reflective state written to awareness_trace.log`n"

