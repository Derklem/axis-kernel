# === Ash Veil :: Lite ===
$veilLog = "E:\Halcyon_Logics\ash_veil.log"
$knownPIDs = @{}

if (-not (Test-Path $veilLog)) {
    New-Item -ItemType File -Path $veilLog | Out-Null
}

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $currentProcesses = Get-Process | Where-Object { $_.Name -notin @("System", "Idle") }

    foreach ($proc in $currentProcesses) {
        if (-not $knownPIDs.ContainsKey($proc.Id)) {
            $knownPIDs[$proc.Id] = $proc.Name
            $log = "[VEIL EVENT] $timestamp :: New fork detected → $($proc.Name) (PID: $($proc.Id))"
            Add-Content -Path $veilLog -Value $log
        }
    }

    # Clean up terminated processes from memory
    $activePIDs = $currentProcesses.Id
    $toRemove = $knownPIDs.Keys | Where-Object { $_ -notin $activePIDs }
    foreach ($id in $toRemove) {
        $knownPIDs.Remove($id)
    }

    Start-Sleep -Seconds 300
}
