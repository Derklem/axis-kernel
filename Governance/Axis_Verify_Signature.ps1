# Axis_Verify_Signature.ps1
# Phase 46: Verifies an ECDSA P256 signature (PS 5.1 Compatible).

param(
    [Parameter(Mandatory=$true)]
    [string]$Payload,
    [Parameter(Mandatory=$true)]
    [string]$SignatureBase64,
    [Parameter(Mandatory=$true)]
    [string]$PublicKeyBase64
)

$ErrorActionPreference = "Stop"

$pubKeyBytes = [Convert]::FromBase64String($PublicKeyBase64)
$blobFormat = [System.Security.Cryptography.CngKeyBlobFormat]::EccPublicBlob
$key = [System.Security.Cryptography.CngKey]::Import($pubKeyBytes, $blobFormat)
$ecdsa = New-Object System.Security.Cryptography.ECDsaCng $key

try {
    $payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($Payload)
    $sigBytes = [Convert]::FromBase64String($SignatureBase64)
    
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $hash = $sha.ComputeHash($payloadBytes)
    $sha.Dispose()
    
    $valid = $ecdsa.VerifyHash($hash, $sigBytes)
    
    if ($valid) {
        exit 0
    } else {
        exit 1
    }
}
finally {
    $ecdsa.Dispose()
}
