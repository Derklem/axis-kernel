# AEGIS_Logic.ps1
# Root directive system for AEGIS – high-level intelligence

$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$thought = "[AEGIS] $timestamp — Directive mode initialized."

# Log to file
$logPath = "E:\AEGIS\core_log.txt"
$thought | Out-File -FilePath $logPath -Append -Encoding UTF8

Write-Host $thought
