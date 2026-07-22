# T09_KeyRing.psm1
# Secure Key Custody for Axis using DPAPI (Windows Data Protection API)
# v1.1: Added Vault Integrity (vault_meta) and Scope Support.

$Root = "D:\Infinite\Infinity"
$SecretsDir = Join-Path $Root "Secrets"
$VaultFile = Join-Path $SecretsDir "keyring.json"

# Ensure DPAPI classes are available
Add-Type -AssemblyName System.Security

function Write-AtomicJson {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)]$Object,
        [int]$Depth = 10
    )

    $tmp = $Path + ".tmp"
    $json = $Object | ConvertTo-Json -Depth $Depth

    # Write tmp
    $json | Set-Content -Path $tmp -Encoding UTF8 -Force

    # Atomic-ish replace
    Move-Item -Path $tmp -Destination $Path -Force
}

function Compute-VaultHash($vault) {
    # Generate a hash of all keys to detect tampering/rollback
    if ($vault.keys -is [System.Collections.IDictionary]) {
        $json = $vault.keys | ConvertTo-Json -Compress
    }
    else {
        # Fallback for PSCustomObject
        $json = $vault.keys | ConvertTo-Json -Compress -Depth 5
    }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $hash = $sha.ComputeHash($bytes)
    return ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Initialize-AxisKeyRing {
    if (-not (Test-Path $SecretsDir)) {
        New-Item -ItemType Directory -Path $SecretsDir | Out-Null
    }
    if (-not (Test-Path $VaultFile)) {
        $init = [ordered]@{
            schema     = "axis.keyring.v1"
            vault_meta = @{ created_ts = (Get-Date).ToString("o"); last_modified_ts = (Get-Date).ToString("o"); container_hash = "" }
            keys       = [ordered]@{}
        }
        $init.vault_meta.container_hash = Compute-VaultHash $init
        $init | ConvertTo-Json -Depth 10 | Set-Content $VaultFile -Encoding UTF8
    }
}

function Get-AxisSecret {
    param(
        [Parameter(Mandatory = $true)][string]$KeyRef,
        [Parameter(Mandatory = $false)][string]$Scope = "CurrentUser" 
    )
    
    if (-not (Test-Path $VaultFile)) { return $null }
    
    $vault = Get-Content $VaultFile -Raw | ConvertFrom-Json
    
    # Integrity Check
    $currentHash = Compute-VaultHash $vault
    if ($currentHash -ne $vault.vault_meta.container_hash) {
        Write-Error "Vault Integrity Failure! The keyring file has been tampered with or corrupted."
        return $null
    }

    if (-not $vault.keys.PSObject.Properties[$KeyRef]) { return $null }
    
    $entry = $vault.keys.$KeyRef
    $blob = if ($entry.blob) { $entry.blob } else { $entry }
    
    if ($entry.PSObject.Properties.Match("status").Count -gt 0 -and $entry.status -eq "REVOKED") {
        Write-Warning "Attempted to retrieve REVOKED secret: $KeyRef"
        return $null
    }

    try {
        # Determine internal scope if encoded in KeyRef
        $dpScope = if ($KeyRef -match "LocalMachine") { [System.Security.Cryptography.DataProtectionScope]::LocalMachine } else { [System.Security.Cryptography.DataProtectionScope]::CurrentUser }
        
        $blobBytes = [System.Convert]::FromBase64String($blob)
        $plainBytes = [System.Security.Cryptography.ProtectedData]::Unprotect($blobBytes, $null, $dpScope)
        return [System.Text.Encoding]::UTF8.GetString($plainBytes)
    }
    catch {
        Write-Error "Failed to decrypt secret for ${KeyRef}: $($_.Exception.Message)"
        return $null
    }
}

function Set-AxisSecret {
    param(
        [Parameter(Mandatory = $true)][string]$KeyRef,
        [Parameter(Mandatory = $true)][string]$Secret,
        [Parameter(Mandatory = $false)][string]$Scope = "CurrentUser"
    )
    
    if ([string]::IsNullOrWhiteSpace($Secret)) { Write-Error "Secret is empty for ${KeyRef}"; return }

    Initialize-AxisKeyRing
    $rawVault = Get-Content $VaultFile -Raw | ConvertFrom-Json
    
    # Rebuild as ordered dictionary for mutation safety in PS 5.1
    $vault = [ordered]@{
        schema     = "axis.keyring.v1"
        vault_meta = $rawVault.vault_meta
        keys       = [ordered]@{}
    }
    if ($rawVault.keys) {
        foreach ($p in $rawVault.keys.PSObject.Properties) { $vault.keys[$p.Name] = $p.Value }
    }

    $dpScope = if ($KeyRef -match "LocalMachine" -or $Scope -eq "LocalMachine") { [System.Security.Cryptography.DataProtectionScope]::LocalMachine } else { [System.Security.Cryptography.DataProtectionScope]::CurrentUser }
    
    $blob = $null
    try {
        $enc = [System.Text.Encoding]::UTF8.GetBytes($Secret)
        $blobBytes = [System.Security.Cryptography.ProtectedData]::Protect($enc, $null, $dpScope)
        $blob = [System.Convert]::ToBase64String($blobBytes)
    }
    catch {
        Write-Error "DPAPI Encryption Failed for ${KeyRef}: $($_.Exception.Message)"
        return
    }

    $newEntry = [ordered]@{
        blob       = [string]$blob
        status     = "ACTIVE"
        created_ts = (Get-Date).ToString("o")
        id_binding = ($KeyRef -split ':')[3]
    }
    
    $vault.keys[$KeyRef] = $newEntry
    $vault.vault_meta.last_modified_ts = (Get-Date).ToString("o")
    $vault.vault_meta.container_hash = Compute-VaultHash $vault
    
    try {
        Write-AtomicJson -Path $VaultFile -Object $vault -Depth 10
    }
    catch {
        Write-Error "Failed to write vault: $($_.Exception.Message)"
        return
    }
    Write-Host "[OK] Secret stored for ${KeyRef}" -ForegroundColor Green
}

function Rotate-AxisSecret {
    param(
        [Parameter(Mandatory = $true)][string]$Identity,
        [Parameter(Mandatory = $true)][string]$NewSecret,
        [string]$Reason = "Routine Rotation"
    )
    
    Initialize-AxisKeyRing
    $vault = Get-Content $VaultFile -Raw | ConvertFrom-Json
    
    $oldRef = Get-AxisKeyRef -Identity $Identity
    Set-AxisSecret -KeyRef $oldRef -Secret $NewSecret
}

function Revoke-AxisKey {
    param([Parameter(Mandatory = $true)][string]$KeyRef, [string]$Reason = "Compromise")
    
    $rawVault = Get-Content $VaultFile -Raw | ConvertFrom-Json
    
    # Rebuild as ordered dictionary
    $vault = [ordered]@{
        schema     = "axis.keyring.v1"
        vault_meta = $rawVault.vault_meta
        keys       = [ordered]@{}
    }
    foreach ($p in $rawVault.keys.PSObject.Properties) { $vault.keys[$p.Name] = $p.Value }

    if (-not $vault.keys[$KeyRef]) { return }
    
    # Robust property update (handle PSCustomObject limitation)
    $oldEntry = $vault.keys[$KeyRef]
    $entry = [ordered]@{}
    foreach ($p in $oldEntry.PSObject.Properties) { $entry[$p.Name] = $p.Value }
    
    $entry.status = "REVOKED"
    $entry.revoked_ts = (Get-Date).ToString("o")
    $entry.reason = $Reason
    
    $vault.keys[$KeyRef] = $entry
    
    $vault.vault_meta.container_hash = Compute-VaultHash $vault
    
    try {
        Write-AtomicJson -Path $VaultFile -Object $vault -Depth 10
    }
    catch {
        # Last resort "nuclear write"
        if (Test-Path $VaultFile) { Remove-Item $VaultFile -Force -ErrorAction SilentlyContinue }
        Start-Sleep -Milliseconds 50
        $vault | ConvertTo-Json -Depth 10 | Set-Content $VaultFile -Encoding UTF8 -Force
    }
    Write-Host "[REVOKED] Key ${KeyRef} has been revoked." -ForegroundColor Red
}

function Get-AxisKeyStatus {
    param([Parameter(Mandatory = $true)][string]$KeyRef)
    if (-not (Test-Path $VaultFile)) { return "UNKNOWN" }
    $vault = Get-Content $VaultFile -Raw | ConvertFrom-Json
    if (-not $vault.keys.PSObject.Properties[$KeyRef]) { 
        # Fallback: Iterate properties to find matching name (PS5.1 colon issue workaround)
        $found = $null
        foreach ($p in $vault.keys.PSObject.Properties) {
            if ($p.Name -eq $KeyRef) { $found = $p.Value; break }
        }
        if (-not $found) { return "MISSING" }
        return $found.status
    }
    return $vault.keys.$KeyRef.status
}

function Get-AxisKeyRef {
    param(
        [Parameter(Mandatory = $true)][string]$Identity,
        [Parameter(Mandatory = $false)][string]$Scope = "CURRENTUSER",
        [Parameter(Mandatory = $false)][string]$Version = "v1"
    )
    # Convention: dpapi:<SCOPE>:axis:<identity_clean>:<version>
    $cleanId = $Identity.Trim() -replace ':', '_'
    $s = $Scope.Trim().ToUpper()
    return "dpapi:$s:axis:$($cleanId):$Version"
}

Export-ModuleMember -Function Get-AxisSecret, Set-AxisSecret, Initialize-AxisKeyRing, Get-AxisKeyRef, Rotate-AxisSecret, Revoke-AxisKey, Get-AxisKeyStatus
