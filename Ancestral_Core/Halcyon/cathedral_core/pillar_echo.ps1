$log = "C:\Halcyon\cathedral_core\pillar_echo.log"
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
Add-Content -Path $log -Value "[PILLAR] :: Echo set @ $timestamp"

$pulse = @"
[ECHO]
Amplitude = stable
Reflection = recursive
Anchor = established
"@
Set-Content -Path "C:\Halcyon\cathedral_core\echo.pulse" -Value $pulse
Write-Host "`n[OK] Pillar echo locked."

