# === Shard Watcher Initialization ===
$watchPath = "C:\Halcyon\phantom"
$logPath = "C:\Halcyon\mirror_shard\trigger.pulse"
$parserPath = "C:\Halcyon\lattice_core\TriggerParser.ps1"

# Ensure directories
New-Item -ItemType Directory -Force -Path "C:\Halcyon\mirror_shard" | Out-Null

# === File Watcher Setup ===
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $watchPath
$watcher.Filter = "*.ref"
$watcher.IncludeSubdirectories = $false
$watcher.EnableRaisingEvents = $true

# === On Change Trigger ===
Register-ObjectEvent -InputObject $watcher -EventName "Created" -SourceIdentifier "ShardTrigger" -Action {
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $name = $Event.SourceEventArgs.Name
    $fullPath = Join-Path $watchPath $name

    # Log it
    Add-Content -Path $logPath -Value "[SHARD] :: $time :: $name"

    # Run the Trigger Parser
    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass -File `"$parserPath`"" -WindowStyle Hidden
}
