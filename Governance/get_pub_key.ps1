$keyName = "axis_anchor_key_primary_v1"
$provider = [System.Security.Cryptography.CngProvider]::MicrosoftSoftwareKeyStorageProvider
if ([System.Security.Cryptography.CngKey]::Exists($keyName, $provider)) {
    $key = [System.Security.Cryptography.CngKey]::Open($keyName, $provider)
    $pub = $key.Export([System.Security.Cryptography.CngKeyBlobFormat]::EccPublicBlob)
    $base64 = [Convert]::ToBase64String($pub)
    $base64 | Out-File "D:\Infinite\Infinity\Governance\anchor_pub_key.b64" -Encoding ascii
    Write-Host "Public Key exported to anchor_pub_key.b64"
} else {
    Write-Error "Key $keyName not found."
}
