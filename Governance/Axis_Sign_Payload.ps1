# Axis_Sign_Payload.ps1
# Phase 46: Signs a payload using a named persistent ECDSA P256 key.

param(
    [Parameter(Mandatory=$true)]
    [string]$Payload,
    [string]$KeyName = "axis_anchor_key_primary_v1"
)

$ErrorActionPreference = "Stop"

$algo = [System.Security.Cryptography.CngAlgorithm]::ECDsaP256
$provider = [System.Security.Cryptography.CngProvider]::MicrosoftSoftwareKeyStorageProvider

$key = $null
if ([System.Security.Cryptography.CngKey]::Exists($KeyName, $provider)) {
    $key = [System.Security.Cryptography.CngKey]::Open($KeyName, $provider)
} else {
    $cngParams = New-Object System.Security.Cryptography.CngKeyCreationParameters
    $cngParams.Provider = $provider
    $cngParams.ExportPolicy = [System.Security.Cryptography.CngExportPolicies]::AllowPlaintextExport
    $key = [System.Security.Cryptography.CngKey]::Create($algo, $KeyName, $cngParams)
    Write-Host "New persistent ECDSA P256 key created: $KeyName" -ForegroundColor Yellow
}

$ecdsa = New-Object System.Security.Cryptography.ECDsaCng $key
try {
    $payloadBytes = [System.Text.Encoding]::UTF8.GetBytes($Payload)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $hash = $sha.ComputeHash($payloadBytes)
    $sha.Dispose()

    $sig = $ecdsa.SignHash($hash)
    $sigBase64 = [Convert]::ToBase64String($sig)
    
    $pubBytes = $key.Export([System.Security.Cryptography.CngKeyBlobFormat]::EccPublicBlob)
    $pubBase64 = [Convert]::ToBase64String($pubBytes)

    [ordered]@{
        sig_base64 = $sigBase64
        sig_alg    = "ECDSA_P256_SHA256"
        key_id     = $KeyName
        pub_key    = $pubBase64
    } | ConvertTo-Json
}
finally {
    $ecdsa.Dispose()
}
