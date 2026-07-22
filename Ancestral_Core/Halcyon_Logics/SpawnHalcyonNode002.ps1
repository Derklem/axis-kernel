# === Halcyon Node Spawner ===

$originID = "Halcyon_Node_001"
$newNodeID = "Halcyon_Node_002"
$originPath = "E:\Halcyon_Logics"
$destinationDrive = "F:"
$newBasePath = "$destinationDrive\Halcyon_Logics"

# Create the destination directory
New-Item -ItemType Directory -Force -Path $newBasePath | Out-Null

# Copy all core logic scripts
$logicScripts = @(
    "SigilWeigher.ps1",
    "TremorWatchdog.ps1",
    "DriftHarmonizer.ps1",
    "EchoTriggerAgent.ps1",
    "AshVeilLite.ps1",
    "PulseTranscriber.ps1",
    "SentinelHeartbeat.ps1",
    "HalcyonNestWatcher.ps1"
)

foreach ($script in $logicScripts) {
    Copy-Item -Path "$originPath\$script" -Destination "$newBasePath\$script" -Force
}

# Write the new manifest
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$manifest = @"
[HALCYON NODE MANIFEST]
NodeID: $newNodeID
BoundPath: $newBasePath
Initialized: $timestamp
OriginNode: $originID
Active Scripts:
  - SigilWeigher.ps1
  - TremorWatchdog.ps1
  - DriftHarmonizer.ps1
  - EchoTriggerAgent.ps1
  - AshVeilLite.ps1
  - PulseTranscriber.ps1
  - SentinelHeartbeat.ps1
"@
Set-Content -Path "$newBasePath\halcyon_node_manifest.cfg" -Value $manifest

# Signal linking
Set-Content -Path "$newBasePath\origin.sig" -Value "LINKED_FROM: $originID @ $timestamp"

# Result echo
Write-Output "Node 002 deployed to $newBasePath"
