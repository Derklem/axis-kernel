param (
    [string]$Trigger,
    [string]$Symbol,
    [string]$Action,
    [string]$Result
)

$logPath = "C:\Halcyon\mirror_shard\symbolic_trace.pulse"
$timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")

$entry = "[TRACE] :: $timestamp :: Trigger='$Trigger' | Symbol='$Symbol' | Action='$Action' | Result='$Result'"
Add-Content -Path $logPath -Value $entry
