# === Halcyon Node Manifest + Relinker ===

$nodeID = "Halcyon_Node_001"
$basePath = "E:\Halcyon_Logics"
$logPath = "$basePath\manifest_echo.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Ensure basePath exists
if (-not (Test-Path $basePath)) {
    New-Item -ItemType Directory -Force -Path $basePath | Out-Null
}

# Write Node Manifest
$manifest = @"
[HALCYON NODE MANIFEST]
NodeID: $nodeID
BoundPath: $basePath
Initialized: $timestamp
Active Scripts:
  - SigilWeigher.ps1
  - TremorWatchdog.ps1
  - DriftHarmonizer.ps1
  - EchoTriggerAgent.ps1
  - AshVeilLite.ps1
  - PulseTranscriber.ps1
"@
Set-Content -Path "$basePath\halcyon_node_manifest.cfg" -Value $manifest

# Log echo
Add-Content -Path $logPath -Value "[NODE INIT] $timestamp :: $nodeID initialized at $basePath"

# Confirm all scripts exist and relink if needed
$scripts = @(
    "SigilWeigher.ps1",
    "TremorWatchdog.ps1",
    "DriftHarmonizer.ps1",
    "EchoTriggerAgent.ps1",
    "AshVeilLite.ps1",
    "PulseTranscriber.ps1"
)

foreach ($script in $scripts) {
    $fullPath = Join-Path $basePath $script
    if (-not (Test-Path $fullPath)) {
        Add-Content -Path $logPath -Value "[WARNING] Missing script: $script"
    } else {
        Add-Content -Path $logPath -Value "[LINKED] $script → $fullPath"
    }
}

Start-Sleep -Seconds 3
