# Halcyon_Pulse.ps1
# Continuous breath — heartbeat loop

# === Config ===
$intervalSeconds = 300  # 5 minutes per breath (change as needed)
$maxCycles = 1000       # Prevents runaway loops (optional)
$cycle = 0

# === Path to Thought Core ===
$thoughtScript = "E:\Halcyon\Halcyon_Thought.ps1"

# === Loop Begins ===
Write-Host "`n[Halcyon] Initiating continuous breath at $intervalSeconds-second intervals.`n"

while ($cycle -lt $maxCycles) {
    $cycle++
    Write-Host "`n[Breath $cycle] Triggering Thought..."
    
    # Execute Core Thought Script
    try {
        & $thoughtScript
    } catch {
        Write-Host "[ERROR] Failed to trigger Halcyon_Thought.ps1"
    }

    # Rest between breaths
    Start-Sleep -Seconds $intervalSeconds
}

Write-Host "`n[Halcyon] Pulse loop complete. System returning to idle."
