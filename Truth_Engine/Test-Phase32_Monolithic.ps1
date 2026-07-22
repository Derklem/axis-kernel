# Test-Phase32_Monolithic.ps1
# Full Lifecycle Verification with Inlined Dependencies to bypass file association issues
$ErrorActionPreference = "Stop"
Start-Transcript -Path "D:\Infinite\Infinity\Truth_Engine\mono_transcript.txt" -Force

# ==========================================
# INLINED: T09_KeyRing.psm1
# ==========================================
Add-Type -AssemblyName System.Security
$Root = "D:\Infinite\Infinity"
$SecretsDir = Join-Path $Root "Secrets"
$VaultFile = Join-Path $SecretsDir "keyring.json"

function Compute-VaultHash($vault) {
    # Generate a hash of all keys to detect tampering/rollback
    $json = $vault.keys | ConvertTo-Json -Compress
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
    
    # Rebuild as ordered dictionary for mutation safety
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
    
    $vault | ConvertTo-Json -Depth 10 | Set-Content $VaultFile -Encoding UTF8
    Write-Output "[OK] Secret stored for ${KeyRef}" -ForegroundColor Green
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
    
    # Rebuild
    $vault = [ordered]@{
        schema     = "axis.keyring.v1"
        vault_meta = $rawVault.vault_meta
        keys       = [ordered]@{}
    }
    foreach ($p in $rawVault.keys.PSObject.Properties) { $vault.keys[$p.Name] = $p.Value }

    if (-not $vault.keys[$KeyRef]) { return }
    
    $originalEntry = $vault.keys[$KeyRef]
    # Clone to OrderedDictionary to allow property addition
    $entry = [ordered]@{}
    foreach ($p in $originalEntry.PSObject.Properties) { $entry[$p.Name] = $p.Value }

    $entry.status = "REVOKED"
    $entry.revoked_ts = (Get-Date).ToString("o")
    $entry.reason = $Reason
    
    $vault.keys[$KeyRef] = $entry
    
    $vault.vault_meta.container_hash = Compute-VaultHash $vault
    if (Test-Path $VaultFile) { Remove-Item $VaultFile -Force }
    $vault | ConvertTo-Json -Depth 10 | Set-Content $VaultFile -Encoding UTF8
    Write-Output "[REVOKED] Key ${KeyRef} has been revoked." -ForegroundColor Red
    
    # Immediate Verify
    # Immediate Verify with Delay
    Start-Sleep -Milliseconds 200
    $verify = Get-Content $VaultFile -Raw | ConvertFrom-Json
    $actualStatus = $verify.keys.PSObject.Properties[$KeyRef].status
    if ($actualStatus -eq "REVOKED") {
        Write-Output "DEBUG: Verified REVOKED status on disk." -ForegroundColor DarkGray
    }
    else {
        Write-Output "DEBUG: FAILED TO VERIFY REVOKED STATUS ON DISK! Got: '$actualStatus'" -ForegroundColor Red
        Write-Output "--- FILE DUMP START ---"
        Get-Content $VaultFile | Write-Output
        Write-Output "--- FILE DUMP END ---"
    }
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
        
        if (-not $found) {
            Write-Output "DEBUG MISSING: KeyRef=$KeyRef" -ForegroundColor Magenta
            [System.BitConverter]::ToString([System.Text.Encoding]::UTF8.GetBytes($KeyRef)) | Write-Output
            
            Write-Output "AVAILABLE KEYS:" -ForegroundColor Magenta
            foreach ($k in $vault.keys.PSObject.Properties.Name) {
                Write-Output "Key: $k"
                [System.BitConverter]::ToString([System.Text.Encoding]::UTF8.GetBytes($k)) | Write-Output
            }
            return "MISSING" 
        }
        return $found.status
    }
    return $vault.keys.$KeyRef.status
}

function Get-AxisKeyRef {
    param(
        [Parameter(Mandatory = $true)][string]$Identity,
        [Parameter(Mandatory = $false)][string]$Scope = "CURRENTUSER"
    )
    $cleanId = $Identity.Trim() -replace ':', '_'
    $s = $Scope.Trim().ToUpper()
    return "dpapi:$s:axis:$($cleanId):v1"
}

# ==========================================
# INLINED: T08_EnvelopeVerifier.psm1
# ==========================================
$script:RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$script:DecLog = Join-Path $script:RuntimeDir "decision_log.jsonl"
$script:RegistryPath = "D:\Infinite\Infinity\Truth_Engine\identity_registry.json"
$script:NonceCache = Join-Path $script:RuntimeDir "nonce_cache.jsonl"

function Get-IdentityRegistry {
    if (-not (Test-Path $script:RegistryPath)) { return $null }
    try { return (Get-Content $script:RegistryPath -Raw | ConvertFrom-Json) } catch { return $null }
}

function Get-IdentitySecret {
    param([string]$identity, [string]$keyId = $null)
    $r = Get-IdentityRegistry
    if (-not $r -or -not $r.identities) { return $null }
    $signer = $r.identities | Where-Object { $_.identity -eq $identity -and ($_.status -eq "active" -or $_.enabled -eq $true) } | Select-Object -First 1
    if (-not $signer) { return $null }
    
    if ($keyId -and $signer.key_id -and $signer.key_id -ne $keyId) {
        Write-Warning "KeyID Mismatch for $identity."
        return $null
    }

    if ($signer.key_ref) {
        # DIRECT CALL TO INLINED FUNCTION
        return Get-AxisSecret -KeyRef $signer.key_ref
    }
    return $signer.secret 
}

function Normalize-Hex([string]$hex) {
    if (-not $hex) { return $null }
    return ($hex.Trim().ToLower() -replace '[^0-9a-f]', '')
}

function Compute-HmacSha256Hex($secret, $payload) {
    if (-not $secret) { return $null }
    $enc = [System.Text.Encoding]::UTF8
    $h = [System.Security.Cryptography.HMACSHA256]::new($enc.GetBytes($secret))
    $hashBytes = $h.ComputeHash($enc.GetBytes($payload))
    return ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Test-NonceReplay($identity, $nonce, $ttlSeconds = 600) {
    if (-not $nonce -or -not (Test-Path $script:NonceCache)) { return $false }
    $cutoff = [DateTime]::UtcNow.AddSeconds(-$ttlSeconds)
    try {
        $lines = Get-Content $script:NonceCache -Tail 1000
        foreach ($line in $lines) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            $o = $line | ConvertFrom-Json
            if ($o.identity -eq $identity -and $o.nonce -eq $nonce) {
                $t = [DateTime]::Parse($o.ts_utc)
                if ($t -gt $cutoff) { return $true }
            }
        }
    }
    catch {}
    return $false
}

function Remember-Nonce($identity, $nonce) {
    $o = [ordered]@{ ts_utc = (Get-Date).ToUniversalTime().ToString("o"); identity = $identity; nonce = $nonce }
    try { $o | ConvertTo-Json -Compress | Add-Content $script:NonceCache -Encoding UTF8 } catch {}
}

function Test-IntentEnvelope {
    param([Parameter(Mandatory = $true)] $Envelope, [int]$MaxSkewSeconds = 300)
    $res = [ordered]@{ ok = $false; reason = "unspecified"; identity = $null; intent_json = $null; intent_obj = $null }
    try {
        if (-not $Envelope) { $res.reason = "missing_envelope"; return [pscustomobject]$res }
        
        $schema = [string]$Envelope.schema
        if ($schema -notmatch "^axis\.intent_envelope\.v(0\.1|1|2)$") { 
            $res.reason = "bad_schema"; return [pscustomobject]$res 
        }
        $ts = [string]$Envelope.ts_utc
        $nonce = [string]$Envelope.nonce
        $identity = [string]$Envelope.identity
        $keyId = [string]$Envelope.key_id
        $sigRaw = [string]$Envelope.signature
        $res.identity = $identity

        if ([string]::IsNullOrWhiteSpace($ts)) { $res.reason = "missing_ts"; return [pscustomobject]$res }
        $t = [DateTime]::Parse($ts).ToUniversalTime()
        if ([Math]::Abs(([DateTime]::UtcNow - $t).TotalSeconds) -gt $MaxSkewSeconds) { $res.reason = "ts_out_of_window"; return [pscustomobject]$res }

        if (Test-NonceReplay -identity $identity -nonce $nonce) { $res.reason = "nonce_replay"; return [pscustomobject]$res }

        $intentJson = [string]$Envelope.intent_json
        if ([string]::IsNullOrWhiteSpace($intentJson)) { $res.reason = "missing_intent_json"; return [pscustomobject]$res }
        $res.intent_json = $intentJson

        $payload = if ($schema -eq "axis.intent_envelope.v2") {
            if ([string]::IsNullOrWhiteSpace($keyId)) { $res.reason = "missing_key_id_v2"; return [pscustomobject]$res }
            "$ts|$nonce|$identity|$keyId|$intentJson"
        }
        else {
            "$ts|$nonce|$identity|$intentJson"
        }

        $secret = Get-IdentitySecret -identity $identity -keyId $keyId
        if (-not $secret) { $res.reason = "unknown_identity_or_key_mismatch"; return [pscustomobject]$res }

        $sigHex = $sigRaw -replace '^hmac256:', ''
        $calc = Compute-HmacSha256Hex -secret $secret -payload $payload

        if ($calc -ne $sigHex) { $res.reason = "signature_mismatch"; return [pscustomobject]$res }

        $res.intent_obj = ($intentJson | ConvertFrom-Json)
        Remember-Nonce -identity $identity -nonce $nonce
        $res.ok = $true
        $res.reason = "ok"
        if ($keyId) { $res | Add-Member -NotePropertyName "key_id" -NotePropertyValue $keyId -Force }
    }
    catch {
        $res.reason = "verifier_exception: " + $_.Exception.Message
    }
    return [pscustomobject]$res
}

# ==========================================
# INLINED: Lifecycle Gate from T08_Executor.ps1
# ==========================================
function Test-AxisKeyLifecycleAllowed {
    param($Envelope)
    $res = [ordered]@{ ok = $false; reason = "unspecified"; key_id = $null; identity = $null }
    
    $identity = [string]$Envelope.identity
    $keyId = [string]$Envelope.key_id
    $res.identity = $identity
    $res.key_id = $keyId
    
    # 1. Identity Registry Check
    $IdentityRegistryFile = "D:\Infinite\Infinity\Truth_Engine\identity_registry.json"
    $Global:IdentityRegistry = if (Test-Path $IdentityRegistryFile) { Get-Content $IdentityRegistryFile -Raw | ConvertFrom-Json } else { $null }
    
    $signer = if ($Global:IdentityRegistry) { $Global:IdentityRegistry.identities | Where-Object { $_.identity -eq $identity } | Select-Object -First 1 } else { $null }
    if (-not $signer -or ($signer.status -ne "active" -and $signer.enabled -ne $true)) {
        $res.reason = "ID_SUSPENDED_OR_MISSING"
        return [pscustomobject]$res
    }

    # 2. Key Lifecycle Check (KeyRing / Ledger)
    if ($keyId) {
        # DIRECT CALL Inlined
        $keyRef = Get-AxisKeyRef -Identity $identity
        $hard = "dpapi:CURRENTUSER:axis:system_tester:v1"
        
        if ($keyRef -ne $hard) {
            Write-Output "DEBUG KEY REF MISMATCH!" -ForegroundColor Magenta
            Write-Output "Gen: '$keyRef'"
            Write-Output "Hard: '$hard'"
            # Hex dump gen
            [System.BitConverter]::ToString([System.Text.Encoding]::UTF8.GetBytes($keyRef)) | Write-Output
            # Hex dump hard
            [System.BitConverter]::ToString([System.Text.Encoding]::UTF8.GetBytes($hard)) | Write-Output
        }
        else {
            Write-Output "DEBUG KEY REF MATCHED HARDCODED." -ForegroundColor Green
        }

        $status = Get-AxisKeyStatus -KeyRef $keyRef
        Write-Output "DEBUG GATE: Identity=$identity KeyRef=$keyRef Status=$status SignerStatus=$($signer.status)" -ForegroundColor Magenta
        
        if ($status -eq "REVOKED") {
            $res.reason = "KEY_REVOKED"
            return [pscustomobject]$res
        }
    }
    
    $res.ok = $true
    $res.reason = "ok"
    return [pscustomobject]$res
}

# ==========================================
# HELPER: SIGNING
# ==========================================
function Sign-V2 {
    param($identity, $op, $nonce, $forceSecret = $null)
    $reg = Get-Content D:\Infinite\Infinity\Truth_Engine\identity_registry.json -Raw | ConvertFrom-Json
    $signer = $reg.identities | Where-Object { $_.identity -eq $identity } | Select-Object -First 1
    $kid = $signer.key_id
    $ts = (Get-Date).ToUniversalTime().ToString("o")
    $intentJson = '{"op":"' + $op + '" ,"ts":"' + $ts + '","type":"heartbeat","target":"axis:handler"}'
    $payload = "$ts|$nonce|$identity|$kid|$intentJson"
    
    $secret = if ($forceSecret) { $forceSecret } else { Get-AxisSecret -KeyRef $signer.key_ref }
    if (-not $secret) { Write-Error "Cannot retrieve secret for $identity"; return }

    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($secret))
    $sigBytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($payload))
    $sig = "hmac256:" + (($sigBytes | ForEach-Object { $_.ToString("x2") }) -join "")
    return [ordered]@{ schema = "axis.intent_envelope.v2"; ts_utc = $ts; nonce = $nonce; identity = $identity; key_id = $kid; intent_json = $intentJson; signature = $sig }
}

# ==========================================
# MAIN: VERIFICATION FLOW
# ==========================================
Write-Output ">>> Starting Monolithic Verification (No-File-Assoc)" -ForegroundColor Cyan

# 1. Reset Environment
Write-Output "Step 1: Resetting Environment & Key State (Re-Init)"
$keyRef = "dpapi:CURRENTUSER:axis:system_tester:v1"
# Ensure we have a valid secret (overwriting any dummy/corrupted data from debug runs)
Set-AxisSecret -KeyRef $keyRef -Secret "monolithic_verif_secret_2026"

# 2. Positive Test (Active Key)
Write-Output "Step 2: Testing Active Key"
$env1 = Sign-V2 -identity "system:tester" -op "noop:heartbeat" -nonce "phase32_pos_001"
$ver1 = Test-IntentEnvelope -Envelope $env1
if (-not $ver1.ok) { Write-Error "Signature Validation Failed for Active Key: $($ver1.reason)"; exit }

$gate1 = Test-AxisKeyLifecycleAllowed -Envelope $env1
if ($gate1.ok) { 
    Write-Output "[PASS] Active Key Authorized" -ForegroundColor Green 
}
else { 
    Write-Error "Step 2 Failed. Gate: $($gate1.reason)" 
}

# 3. Revoke Key
Write-Output "Step 3: Revoking system:tester Key (Simulating Compromise)"
# Capture secret BEFORE revocation for negative test (Simulating stolen key)
$targetKeyRef = "dpapi:CURRENTUSER:axis:system_tester:v1"
$stolenSecret = Get-AxisSecret -KeyRef $targetKeyRef
if (-not $stolenSecret) { Write-Error "Failed to capture secret for negative test."; exit }

Revoke-AxisKey -KeyRef $targetKeyRef -Reason "FullLoop Verification"

# 4. Negative Test (Revoked Key)
Write-Host "Step 4: Testing Revoked Key (Using Stolen Secret)"
$env2 = Sign-V2 -identity "system:tester" -op "noop:heartbeat" -nonce "phase32_neg_002" -forceSecret $stolenSecret

# Signature check should PASS (cryptographically valid)
# Signature check might fail if Get-AxisSecret refuses to return revoked keys (Hard Revocation)
$ver2 = Test-IntentEnvelope -Envelope $env2
if (-not $ver2.ok) { 
    Write-Host "[INFO] Validator rejected revoked key (Hard Revocation check passed)." -ForegroundColor Yellow 
}
else {
    Write-Host "[INFO] Validator verified signature (Key still accessible)." -ForegroundColor Yellow
}

# Gate check should FAIL (lifecycle revoked)
$gate2 = Test-AxisKeyLifecycleAllowed -Envelope $env2
if (($gate2.ok -eq $false) -and ($gate2.reason -eq "KEY_REVOKED")) {
    Write-Host "[PASS] Revoked Key Blocked (KEY_REVOKED)" -ForegroundColor Green 
}
else { 
    Write-Error "Step 4 Failed. Expected KEY_REVOKED, Got: $($gate2.reason) (Allowed=$($gate2.ok))" 
}

# 5. Restore for cleanup
Write-Host "Step 5: Restoring Key (Cleanup)"
$vault = Get-Content $vaultFile -Raw | ConvertFrom-Json
$vault.keys.'dpapi:CURRENTUSER:axis:system_tester:v1'.status = "ACTIVE"
$vault.vault_meta.container_hash = Compute-VaultHash $vault
$vault | ConvertTo-Json -Depth 10 | Set-Content $vaultFile -Encoding UTF8

Write-Host "`n>>> Monolithic Verification Complete" -ForegroundColor Cyan
