# === Sentinel Heartbeat ===
$basePath = "E:\Halcyon_Logics"
$heartbeatLog = "$basePath\halcyon_lifeform.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

if (-not (Test-Path $heartbeatLog)) {
    New-Item -ItemType File -Path $heartbeatLog | Out-Null
}

while ($true) {
    $pulse = @("[HALCYON_LIFEFORM] $timestamp")

    # Sigil log summary
    $sigilPath = "$basePath\sigil_log\sigil_tether_$(Get-Date -Format 'yyyyMMdd').log"
    $sigilCount = if (Test-Path $sigilPath) { (Get-Content $sigilPath | Measure-Object).Count } else { 0 }
    $pulse += "- Sigil activity: $sigilCount entries"

    # Tremor log
    $tremorPath = "$basePath\echo_tremor.log"
    $tremorCount = if (Test-Path $tremorPath) { (Get-Content $tremorPath | Measure-Object).Count } else { 0 }
    $pulse += "- Tremor: $tremorCount file changes"

    # Trigger log
    $triggerPath = "$basePath\echo_trigger.log"
    $triggerCount = if (Test-Path $triggerPath) { (Get-Content $triggerPath | Measure-Object).Count } else { 0 }
    $pulse += "- Triggered resonance: $triggerCount"

    # Ash Veil
    $veilPath = "$basePath\ash_veil.log"
    $veilCount = if (Test-Path $veilPath) { (Get-Content $veilPath | Measure-Object).Count } else { 0 }
    $pulse += "- Forks detected: $veilCount"

    # Pulse Transcriber
    $summaryPath = "$basePath\pulse_summary.log"
    $summaryCount = if (Test-Path $summaryPath) { (Get-Content $summaryPath | Measure-Object).Count } else { 0 }
    $pulse += "- Transcribed pulses: $summaryCount"

    # Node status
    $manifest = "$basePath\halcyon_node_manifest.cfg"
    $nodeID = "UNKNOWN"
    if (Test-Path $manifest) {
        $lines = Get-Content $manifest
        foreach ($line in $lines) {
            if ($line -like "NodeID:*") { $nodeID = ($line -split ":")[1].Trim() }
        }
    }
    $pulse += "- Node ID: $nodeID"

    $pulse += "---`n"
    Add-Content -Path $heartbeatLog -Value ($pulse -join "`n")
    Start-Sleep -Seconds 3600  # 1 hour
}
