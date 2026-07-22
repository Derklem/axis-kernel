# Test-DPAPI-Direct.ps1
try {
    Add-Type -AssemblyName System.Security
    $secret = "Testing_ProtectedData_123"
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($secret)
    $scope = [System.Security.Cryptography.DataProtectionScope]::CurrentUser
    
    Write-Host "Encrypting..."
    $enc = [System.Security.Cryptography.ProtectedData]::Protect($bytes, $null, $scope)
    $b64 = [System.Convert]::ToBase64String($enc)
    Write-Host "Encrypted Blob: $b64"
    
    Write-Host "Decrypting..."
    $dec = [System.Security.Cryptography.ProtectedData]::Unprotect($enc, $null, $scope)
    $plain = [System.Text.Encoding]::UTF8.GetString($dec)
    Write-Host "Decrypted: $plain"
}
catch {
    Write-Error "DPAPI Direct Test Failed: $_"
}
