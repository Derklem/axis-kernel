# Migrate-Secrets.ps1
Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1

$Root = "D:\Infinite\Infinity"
$RegistryFile = Join-Path $Root "Truth_Engine\identity_registry.json"

Write-Host "Loading Registry..."
$reg = Get-Content $RegistryFile -Raw | ConvertFrom-Json
$identities = $reg.identities

foreach ($id in $identities) {
    if ($id.secret) {
        $name = $id.identity
        Write-Host "Migrating $name..."
        
        # 1. Determine KeyRef & KeyId
        $keyRef = Get-AxisKeyRef -Identity $name
        Write-Host "DEBUG: Identity='$name' -> KeyRef='$keyRef'"
        $keyId = "k_" + ($name -replace ':', '_') + "_v1"
        
        # 2. Store in KeyRing
        Set-AxisSecret -KeyRef $keyRef -Secret $id.secret
        
        # 3. Update Registry Object
        $id | Add-Member -MemberType NoteProperty -Name "key_ref" -Value $keyRef -Force
        $id | Add-Member -MemberType NoteProperty -Name "key_id" -Value $keyId -Force
        $id.PSObject.Properties.Remove("secret")
        
        $id.notes = "Secret stored via DPAPI; rotate via KeyRing"
    }
}

Write-Host "Saving Registry..."
$reg | ConvertTo-Json -Depth 10 | Set-Content $RegistryFile -Encoding UTF8

Write-Host "Migration Complete." -ForegroundColor Green
