$key = [System.Security.Cryptography.CngKey]::Create([System.Security.Cryptography.CngAlgorithm]::ECDsaP256)
$ecdsa = New-Object System.Security.Cryptography.ECDsaCng $key
$payload = "TEST"
$payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($payload)
$sha = [System.Security.Cryptography.SHA256]::Create()
$hash = $sha.ComputeHash($payloadBytes)
$sha.Dispose()
$sig = $ecdsa.SignHash($hash)
Write-Host "SIG_BASE64:$([Convert]::ToBase64String($sig))"
$pub = $key.Export([System.Security.Cryptography.CngKeyBlobFormat]::EccPublicBlob)
Write-Host "PUB_BASE64:$([Convert]::ToBase64String($pub))"
$isValid = $ecdsa.VerifyHash($hash, $sig)
Write-Host "VALID:$isValid"
$ecdsa.Dispose()
