# T08_LifecycleGate.psm1
# Phase 33/34/35/Hardened: Centralized Lifecycle Gate Logic
# Exports: Test-AxisKeyLifecycleAllowed, Normalize-AxisIdentityRecord

# --- Dependencies ---
$KeyRingModule = "D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1"
if (Test-Path $KeyRingModule) { Import-Module $KeyRingModule -Force -ErrorAction SilentlyContinue }

function Normalize-AxisIdentityRecord {
    param($rec)
    if (-not $rec) { return $null }
    $status = if ($rec.status) { $rec.status } elseif ($rec.PSObject.Properties.Name -contains "enabled") { if ($rec.enabled) { "active" } else { "disabled" } } else { "disabled" }
    $caps = if ($rec.capabilities -is [System.Array]) { $rec.capabilities } elseif ($rec.capabilities -ne $null) { @($rec.capabilities) } else { @() }
    return [pscustomobject]@{
        identity     = [string]$rec.identity
        status       = [string]$status
        capabilities = $caps
        key_ref      = [string]$rec.key_ref
        key_id       = [string]$rec.key_id
    }
}

function Test-AxisKeyLifecycleAllowed {
    # Phase 35: Key Lifecycle & Scope Gate (Hardened)
    param(
        $Envelope,
        [string]$OpKey = "unknown", 
        [switch]$NoCache
    )

    $res = [ordered]@{
        ok       = $false
        reason   = "unspecified"
        key_id   = $null
        identity = $null
        details  = @{}
    }

    $identity = [string]$Envelope.identity
    $envKeyId = [string]$Envelope.key_id
    $res.identity = $identity
    $res.key_id = $envKeyId

    # 0) Envelope Binding (Fail Closed)
    if ([string]::IsNullOrWhiteSpace($envKeyId)) {
        $res.reason = "BLOCKED_KEY_MISSING"
        return [pscustomobject]$res
    }

    # 1) Identity Registry (Status Check + Hash Update)
    if ($NoCache -or -not $Global:IdentityRegistry -or -not $Global:IdentityRegistry_TS -or $Global:IdentityRegistry_TS -lt (Get-Date).AddSeconds(-5)) {
        $IdentityRegistryFile = "D:\Infinite\Infinity\Truth_Engine\identity_registry.json"
        if (Test-Path $IdentityRegistryFile) {
            try {
                $rawReg = Get-Content $IdentityRegistryFile -Raw
                $Global:IdentityRegistry = $rawReg | ConvertFrom-Json
                $Global:IdentityRegistry_Hash = "sha256:" + ([BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($rawReg))) -replace "-", "").ToLower()
                $Global:IdentityRegistry_TS = Get-Date
            }
            catch {
                $res.reason = "BLOCKED_ID_REGISTRY_READ_FAILED"
                return [pscustomobject]$res
            }
        }
        else {
            $res.reason = "BLOCKED_ID_REGISTRY_MISSING"
            return [pscustomobject]$res
        }
    }

    $raw = $Global:IdentityRegistry.identities | Where-Object { $_.identity -eq $identity } | Select-Object -First 1
    $signer = Normalize-AxisIdentityRecord $raw
    if (-not $signer -or $signer.status -ne "active") {
        $res.reason = "BLOCKED_ID_SUSPENDED"
        return [pscustomobject]$res
    }

    # 2) Keyring Lookup (Canonical Source + Hash Update)
    if ($NoCache -or -not $Global:Keyring -or -not $Global:Keyring_TS -or $Global:Keyring_TS -lt (Get-Date).AddSeconds(-30)) {
        $KeyringFile = "D:\Infinite\Infinity\Truth_Engine\keyring.json"
        if (Test-Path $KeyringFile) {
            try {
                $rawKr = Get-Content $KeyringFile -Raw
                $Global:Keyring = $rawKr | ConvertFrom-Json
                $Global:Keyring_Hash = "sha256:" + ([BitConverter]::ToString([System.Security.Cryptography.SHA256]::Create().ComputeHash([Text.Encoding]::UTF8.GetBytes($rawKr))) -replace "-", "").ToLower()
                $Global:Keyring_TS = Get-Date
            }
            catch {
                $res.reason = "BLOCKED_KEYRING_READ_FAILED"
                return [pscustomobject]$res
            }
        }
        else {
            $res.reason = "BLOCKED_KEYRING_MISSING"
            return [pscustomobject]$res
        }
    }

    $keyRecord = $Global:Keyring.keys | Where-Object { $_.key_id -eq $envKeyId } | Select-Object -First 1
    if (-not $keyRecord) {
        $res.reason = "BLOCKED_KEY_UNKNOWN"
        return [pscustomobject]$res
    }

    # 3) Binding Check
    if ($keyRecord.identity -ne $identity) {
        $res.reason = "BLOCKED_KEY_UNBOUND"
        return [pscustomobject]$res
    }

    # 4) Revocation Ledger Enforcement (AUTHORITATIVE OVER KEYRING STATUS)
    $RevokeFile = "D:\Infinite\Infinity\Truth_Engine\revocation_ledger.jsonl"
    if (Test-Path $RevokeFile) {
        try {
            # Window/Tail Risk Hardening:
            $LedgerContent = Get-Content $RevokeFile
            # Simple Hardening: If ledger is huge and we only check tail, fail closed or implement index.
            # For Phase 35, we'll scan the full ledger if it's manageable (< 5000 lines).
            if ($LedgerContent.Count -gt 5000) {
                # In a production system, we'd use a cached index/snapshot.
                # Fail closed to prevent bypass via 'ledger drown'.
                $res.reason = "BLOCKED_REVOCATION_LEDGER_OVERFLOW"
                return [pscustomobject]$res
            }

            # Find last event for this key in ledger order (most recent wins)
            $lastEvent = $LedgerContent | ForEach-Object { try { $_ | ConvertFrom-Json } catch { $null } } | 
            Where-Object { $_ -and $_.key_id -eq $envKeyId -and ($_.event_type -in "KEY_REVOKED", "KEY_SUSPENDED", "KEY_REACTIVATED") } | 
            Select-Object -Last 1
            
            if ($lastEvent -and ($lastEvent.event_type -in "KEY_REVOKED", "KEY_SUSPENDED")) {
                $res.reason = "BLOCKED_KEY_REVOKED_LEDGER"
                $res.details["revocation_event"] = $lastEvent.event_id
                $res.details["revocation_head_hash"] = $lastEvent.hash
                return [pscustomobject]$res
            }

            # Also capture head for audit log consistency on SUCCESS
            $res.details["revocation_head_hash"] = ($LedgerContent | ForEach-Object { try { $_ | ConvertFrom-Json } catch { $null } } | Where-Object { $_ -and $_.hash } | Select-Object -Last 1).hash
        }
        catch {
            $res.reason = "BLOCKED_REVOCATION_LEDGER_ERROR"
            return [pscustomobject]$res
        }
    }

    # 5) Key Status Check (Advisory Keyring Status)
    if ($keyRecord.status -ne "active") {
        $res.reason = "BLOCKED_KEY_" + $keyRecord.status.ToUpper()
        return [pscustomobject]$res
    }

    # 6) Time Window Check
    $now = (Get-Date).ToUniversalTime()
    if ($keyRecord.not_before_utc) {
        $nbf = [DateTime]::Parse($keyRecord.not_before_utc).ToUniversalTime()
        if ($now -lt $nbf) {
            $res.reason = "BLOCKED_KEY_NOT_YET_VALID"
            return [pscustomobject]$res
        }
    }
    if ($keyRecord.expires_utc) {
        $exp = [DateTime]::Parse($keyRecord.expires_utc).ToUniversalTime()
        if ($now -gt $exp) {
            $res.reason = "BLOCKED_KEY_EXPIRED"
            return [pscustomobject]$res
        }
    }

    # 7) Scope Check (OpKey) - Normalized
    if ([string]::IsNullOrWhiteSpace($OpKey) -or $OpKey -eq "unknown") {
        $res.reason = "BLOCKED_KEY_SCOPE_UNKNOWN_OP"
        return [pscustomobject]$res
    }

    $normOp = $OpKey.Trim().ToLowerInvariant()
    $allowed = $false
    foreach ($scope in $keyRecord.scopes) {
        $normScope = $scope.Trim().ToLowerInvariant()
        if ($normScope -eq "*") { $allowed = $true; break }
        if ($normScope -eq $normOp) { $allowed = $true; break }
        if ($normScope.EndsWith("*")) {
            $prefix = $normScope.Substring(0, $normScope.Length - 1)
            if ($normOp.StartsWith($prefix)) { $allowed = $true; break }
        }
    }

    if (-not $allowed) {
        $res.reason = "BLOCKED_KEY_SCOPE"
        $res.details["op_key"] = $OpKey
        return [pscustomobject]$res
    }

    $res.ok = $true
    $res.reason = "ok"
    return [pscustomobject]$res
}

Export-ModuleMember -Function Test-AxisKeyLifecycleAllowed, Normalize-AxisIdentityRecord
