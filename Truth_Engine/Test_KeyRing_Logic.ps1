# Test_KeyRing_Logic.ps1
Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1

$id = "portal:maya_phone"
Write-Host "Testing with Identity: $id"

$clean = $id -replace ':', '_'
Write-Host "Manual Clean: $clean"

$ref2 = "dpapi:CURRENTUSER:axis:$($clean):v1"
Write-Host "Sub-expression Test: $ref2"

if ($ref -like "*maya*") {
    Write-Host "PASS" -ForegroundColor Green
}
else {
    Write-Host "FAIL" -ForegroundColor Red
}
