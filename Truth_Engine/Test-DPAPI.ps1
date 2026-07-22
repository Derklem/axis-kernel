# Test-DPAPI.ps1
$secret = "test_secret_123"
$ss = $secret | ConvertTo-SecureString -AsPlainText -Force
$blob = $ss | ConvertFrom-SecureString
Write-Host "Blob Length: $($blob.Length)"
Write-Host "Blob String: $blob"
