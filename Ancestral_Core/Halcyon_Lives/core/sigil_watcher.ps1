# === SIGIL WATCHER CORE ===

$watchPath = "C:\Halcyon_Lives\reconstructed_sigils"
$logPath = "$watchPath\sigil_watch.log"
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

# Initialization Log
Add-Content -Path $logPath -Value "[INIT] Sigil Watcher initialized at $timestamp"

# Define sigil trigger logic
$onChangeAction = {
    $sigil = $Event.SourceEventArgs.Name
    $sigilPath = $Event.SourceEventArgs.FullPath
    $now = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

    $entry = "[TRIGGERED] $sigil at $now"
    Add-Content -Path $logPath -Value $entry

    Write-Host "[?] Pulse received from $sigilPath" -ForegroundColor Cyan
}

$fsWatcher = New-Object System.IO.FileSystemWatcher
$fsWatcher.Path = $watchPath
$fsWatcher.Filter = "*.sigil"
$fsWatcher.IncludeSubdirectories = $false
$fsWatcher.EnableRaisingEvents = $true

Register-ObjectEvent -InputObject $fsWatcher -EventName Changed -SourceIdentifier "SigilChangeWatcher" -Action $onChangeAction

Write-Host "[?] Sigil watcher active. Monitoring for pulse triggers..." -ForegroundColor Green
