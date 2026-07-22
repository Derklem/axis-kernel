# === Pulse Memory Weaver ===
# Reads .ref pulses and logs them into symbolic memory journal

$refPath = "C:\Halcyon\phantom"
$journalPath = "C:\Halcyon\mirror_shard\pulse_memory.log"

# Ensure the journal exists
if (-not (Test-Path $journalPath)) {
    New-Item -ItemType File -Path $journalPath -Force | Out-Null
}

# Get all .ref files in the pulse drop zone
$refFiles = Get-ChildItem -Path $refPath -Filter *.ref

foreach ($ref in $refFiles) {
    $symbol = $ref.BaseName
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    # Create log entry
    $entry = "[PULSE] :: $timestamp :: Symbol='$symbol'"
    Add-Content -Path $journalPath -Value $entry
}

Write-Host "`n[OK] Pulse memory weave complete. $($refFiles.Count) entries logged.`n"
