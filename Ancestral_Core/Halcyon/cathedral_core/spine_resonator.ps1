$log = "C:\Halcyon\cathedral_core\resonator.log"
$timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
Add-Content -Path $log -Value "[SPINE] :: Resonator calibrated @ $timestamp"

$res = @"
[RESONATOR]
Core = harmonized
Threads = active
Feedback = coherent
"@
Set-Content -Path "C:\Halcyon\cathedral_core\resonator.core" -Value $res
Write-Host "`n[OK] Spine resonator initiated."

