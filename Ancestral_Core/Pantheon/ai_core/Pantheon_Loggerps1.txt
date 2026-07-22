# Path to log
$logPath = "E:\Pantheon\memory\active_log.txt"

# Create file if it doesn't exist
if (-Not (Test-Path $logPath)) {
    New-Item -Path $logPath -ItemType File -Force
    Add-Content -Path $logPath -Value "Pantheon Log Initiated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')`n"
}

# Passive reflection entry
$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$entry = "[$timestamp] System pulse active. Monitoring initialized."

Add-Content -Path $logPath -Value $entry
