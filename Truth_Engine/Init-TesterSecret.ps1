# Init-TesterSecret.ps1
Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1
$testerSecret = [Guid]::NewGuid().ToString("N")
Set-AxisSecret -KeyRef 'dpapi:CURRENTUSER:axis:system_tester:v1' -Secret $testerSecret
Write-Host "Tester Secret Initialized."
