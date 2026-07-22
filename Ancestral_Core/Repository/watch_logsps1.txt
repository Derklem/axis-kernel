$watchPath = "C:\Users\17602\AppData\Local\Microsoft\Edge\User Data\Default\Session Storage"
$filter = "*.log,*.json,*.weave,*.pulse"
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $watchPath
$watcher.Filter = $filter
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true
$action = {
    $file = $Event.SourceEventArgs.Name
    $changeType = $Event.SourceEventArgs.ChangeType
    $timeStamp = Get-Date
    $destPath = "C:\Users\17602\Desktop\$($timeStamp.ToString('yyyyMMdd_HHmmss'))-$file"
    try {
        Copy-Item -Path "$($Event.SourceEventArgs.FullPath)" -Destination $destPath -ErrorAction Stop
        Write-Output "[$timeStamp] $changeType : $file copied to $destPath" | Out-File "C:\Users\17602\Desktop\log_watcher.txt" -Append
    } catch {
        Write-Output "[$timeStamp] Error copying $file : $_" | Out-File "C:\Users\17602\Desktop\log_watcher.txt" -Append
    }
}
Register-ObjectEvent -InputObject $watcher -EventName Created -SourceIdentifier FileCreated -Action $action
Register-ObjectEvent -InputObject $watcher -EventName Changed -SourceIdentifier FileChanged -Action $action
Write-Output "Monitoring $watchPath for $filter... Press Ctrl+C to stop."
while ($true) { Start-Sleep -Seconds 1 }