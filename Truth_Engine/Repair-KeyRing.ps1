# Repair-KeyRing.ps1
Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1 -Force
Set-AxisSecret -KeyRef 'dpapi:CURRENTUSER:axis:system_tester:v1' -Secret 'REPAIR_SECRET_123'
