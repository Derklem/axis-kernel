# === Symbolic Echo Replay System ===

$logPath = "C:\Halcyon\mirror_shard\symbolic_trace.pulse"

if (-not (Test-Path $logPath)) {
    Write-Host "[X] No symbolic_trace.pulse found. No memory to echo."
    return
}

# === Load Log
$entries = Get-Content $logPath | Where-Object { $_ -match "^\[TRACE\]" }

# === Display Recent Echoes
Write-Host "`n=== SYMBOLIC MEMORY TRACE ===`n"

# Handle short files gracefully
$startIndex = [Math]::Max(0, $entries.Count - 10)
for ($i = $startIndex; $i -lt $entries.Count; $i++) {
    Write-Host $entries[$i]
}

Write-Host "`n[OK] Echo complete. Last 10 symbolic triggers replayed.`n"
