<#
.SYNOPSIS
  Axis Identity Guard (Layer 6) - Hardened
.DESCRIPTION
  Verifies authenticity and authorization of incoming Intent Envelopes (Portal/Remote).
  Supports DEV_SHARED_SECRET via HMAC-SHA256.
  Enforces replay resistance (ts window + nonce cache) and capability checks.
#>

$script:IdentityRegistryPath = "D:\Infinite\Infinity\Runtime\Identity\identity_registry.json"
$script:VerbRegistryPath = "D:\Infinite\Infinity\Runtime\Policy\verb_registry.json"
$script:StatePath = "D:\Infinite\Infinity\Runtime\Identity\Identity_State.json"

# Replay policy
$script:MaxSkewSeconds = 120     # allow 2 min clock skew
$script:MaxAgeSeconds = 300     # accept envelopes up to 5 min old
$script:NonceCacheSize = 200     # per identity rolling cache

function Get-IdentityRegistry {
    if (Test-Path $script:IdentityRegistryPath) {
        try { return (Get-Content $script:IdentityRegistryPath -Raw | ConvertFrom-Json) } catch { return $null }
    }
    return $null
}

function Get-VerbRegistry {
    if (Test-Path $script:VerbRegistryPath) {
        try { return (Get-Content $script:VerbRegistryPath -Raw | ConvertFrom-Json) } catch { return $null }
    }
    return $null
}

function Get-IdentityState {
    if (Test-Path $script:StatePath) {
        try { return (Get-Content $script:StatePath -Raw | ConvertFrom-Json) } catch { }
    }
    return ([pscustomobject]@{ global_anomaly_ema = 0; metrics = @{}; nonce_cache = @{} })
}

function Save-IdentityState($state) {
    if (Get-Command Write-AtomicJson -ErrorAction SilentlyContinue) {
        Write-AtomicJson -Path $script:StatePath -Data $state
    }
    else {
        $state | ConvertTo-Json -Depth 10 | Set-Content $script:StatePath -Force
    }
}

function ConstantTimeEqualsHex {
    param(
        [Parameter(Mandatory = $true)][string]$a,
        [Parameter(Mandatory = $true)][string]$b
    )
    # normalize
    $a = $a.Trim().ToLower()
    $b = $b.Trim().ToLower()
    if ($a.Length -ne $b.Length) { return $false }

    $diff = 0
    for ($i = 0; $i -lt $a.Length; $i++) {
        $diff = $diff -bor ([byte][char]$a[$i] -bxor [byte][char]$b[$i])
    }
    return ($diff -eq 0)
}

function Test-ReplayWindow {
    param(
        [Parameter(Mandatory = $true)]$Envelope
    )

    # Require ts + nonce
    if (-not $Envelope.ts_utc -or -not $Envelope.nonce) {
        return @{ ok = $false; reason = "MISSING_TS_OR_NONCE" }
    }

    # Parse ts_utc
    $ts = $null
    try { $ts = [DateTime]::Parse($Envelope.ts_utc).ToUniversalTime() } catch {
        return @{ ok = $false; reason = "BAD_TS_FORMAT" }
    }

    $now = (Get-Date).ToUniversalTime()
    $age = ($now - $ts).TotalSeconds
    $skew = ($ts - $now).TotalSeconds

    if ($skew -gt $script:MaxSkewSeconds) { return @{ ok = $false; reason = "TS_FROM_FUTURE" } }
    if ($age -gt $script:MaxAgeSeconds) { return @{ ok = $false; reason = "TS_EXPIRED" } }

    # Nonce replay cache
    $state = Get-IdentityState
    if (-not $state.nonce_cache) { $state | Add-Member -NotePropertyName nonce_cache -NotePropertyValue @{} -Force }

    $id = [string]$Envelope.identity
    if (-not $state.nonce_cache.$id) { $state.nonce_cache.$id = @() }

    $cache = @($state.nonce_cache.$id)

    if ($cache -contains $Envelope.nonce) {
        return @{ ok = $false; reason = "REPLAY_NONCE" }
    }

    # Push and trim
    $cache = @($cache + @([string]$Envelope.nonce))
    if ($cache.Count -gt $script:NonceCacheSize) {
        $cache = $cache[ - $script:NonceCacheSize..-1]
    }

    $state.nonce_cache.$id = $cache
    Save-IdentityState $state

    return @{ ok = $true }
}

function Update-IdentityState {
    param([string]$Identity, [string]$Result)

    $state = Get-IdentityState
    if (-not $state.metrics) { $state | Add-Member -NotePropertyName metrics -NotePropertyValue @{} -Force }

    if (-not $state.metrics.$Identity) {
        $state.metrics.$Identity = [pscustomobject]@{ successes = 0; fail_sig = 0; fail_cap = 0; last_seen = $null; fail_replay = 0; fail_struct = 0 }
    }

    $m = $state.metrics.$Identity
    $m.last_seen = (Get-Date).ToUniversalTime().ToString("o")

    switch ($Result) {
        "SUCCESS" { $m.successes++ }
        "FAIL_SIG" { $m.fail_sig++ }
        "FAIL_CAP" { $m.fail_cap++ }
        "FAIL_REPLAY" { $m.fail_replay++ }
        "FAIL_STRUCT" { $m.fail_struct++ }
    }

    if (-not $state.global_anomaly_ema) { $state.global_anomaly_ema = 0 }

    if ($Result -like "FAIL*") {
        $state.global_anomaly_ema = [Math]::Min(100, $state.global_anomaly_ema + 10)
    }
    else {
        $state.global_anomaly_ema = [Math]::Max(0, $state.global_anomaly_ema * 0.9)
    }

    Save-IdentityState $state
}

function Test-IntentEnvelope {
    param(
        [Parameter(Mandatory = $true)] $Envelope
    )

    # 1) Structural validation (fail closed)
    if (-not $Envelope.identity -or -not $Envelope.signature) {
        Update-IdentityState -Identity ([string]$Envelope.identity) -Result "FAIL_STRUCT"
        return @{ ok = $false; reason = "MALFORMED_ENVELOPE" }
    }

    # Prefer intent_json to avoid canonicalization mismatch
    $intentJson = $Envelope.intent_json
    if (-not $intentJson) {
        # fallback: accept object intent, but this risks canonical mismatch with browser signer
        if (-not $Envelope.intent) {
            Update-IdentityState -Identity ([string]$Envelope.identity) -Result "FAIL_STRUCT"
            return @{ ok = $false; reason = "MALFORMED_ENVELOPE" }
        }
        $intentJson = ($Envelope.intent | ConvertTo-Json -Depth 10 -Compress)
    }

    # 2) Identity lookup
    $reg = Get-IdentityRegistry
    if (-not $reg -or -not $reg.identities -or -not $reg.identities.($Envelope.identity)) {
        Update-IdentityState -Identity ([string]$Envelope.identity) -Result "FAIL_STRUCT"
        return @{ ok = $false; reason = "UNKNOWN_IDENTITY"; identity = $Envelope.identity }
    }
    $idRecord = $reg.identities.($Envelope.identity)

    # 3) Replay checks (ts + nonce)
    $replay = Test-ReplayWindow -Envelope $Envelope
    if (-not $replay.ok) {
        Update-IdentityState -Identity $Envelope.identity -Result "FAIL_REPLAY"
        return @{ ok = $false; reason = $replay.reason; identity = $Envelope.identity }
    }

    # 4) Crypto verification (default deny)
    $valid = $false

    if ($idRecord.crypto_mode -eq "DEV_SHARED_SECRET") {
        if ($Envelope.signature -match "^hmac256:(.+)$") {
            $providedHash = $Matches[1]
            $secret = [string]$idRecord.shared_secret
            if ([string]::IsNullOrWhiteSpace($secret)) {
                $valid = $false
            }
            else {
                $payload = "{0}|{1}|{2}|{3}" -f $Envelope.ts_utc, $Envelope.nonce, $Envelope.identity, $intentJson

                $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($secret))
                try {
                    $calcBytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($payload))
                }
                finally {
                    $hmac.Dispose()
                }

                $calcHash = ([BitConverter]::ToString($calcBytes) -replace "-", "").ToLower()
                $valid = ConstantTimeEqualsHex -a $providedHash -b $calcHash
            }
        }
    }
    elseif ($idRecord.crypto_mode -eq "ED25519") {
        # Not implemented yet: keep DENY until real verify exists
        $valid = $false
    }
    else {
        # Unknown crypto mode: deny
        $valid = $false
    }

    if (-not $valid) {
        Update-IdentityState -Identity $Envelope.identity -Result "FAIL_SIG"
        return @{ ok = $false; reason = "INVALID_SIGNATURE"; identity = $Envelope.identity }
    }

    # 5) Parse verified intent JSON (post-verification)
    $intentObj = $null
    try { $intentObj = $intentJson | ConvertFrom-Json } catch {
        Update-IdentityState -Identity $Envelope.identity -Result "FAIL_STRUCT"
        return @{ ok = $false; reason = "BAD_INTENT_JSON"; identity = $Envelope.identity }
    }

    # 6) Capability check (fail closed if registry missing)
    $vReg = Get-VerbRegistry
    if (-not $vReg -or -not $vReg.verbs) {
        Update-IdentityState -Identity $Envelope.identity -Result "FAIL_CAP"
        return @{ ok = $false; reason = "VERB_REGISTRY_MISSING"; identity = $Envelope.identity }
    }

    $verb = $intentObj.verb
    if (-not $verb) { $verb = $intentObj.type }
    if (-not $verb) {
        Update-IdentityState -Identity $Envelope.identity -Result "FAIL_CAP"
        return @{ ok = $false; reason = "MISSING_VERB"; identity = $Envelope.identity }
    }

    if ($vReg.aliases -and $vReg.aliases.$verb) { $verb = $vReg.aliases.$verb }

    $verbRecord = $vReg.verbs.$verb
    if ($verbRecord -and $verbRecord.required_capability) {
        $requiredCap = $verbRecord.required_capability
        if (-not $idRecord.capabilities -or ($idRecord.capabilities -notcontains $requiredCap)) {
            Update-IdentityState -Identity $Envelope.identity -Result "FAIL_CAP"
            return @{ ok = $false; reason = "MISSING_CAPABILITY"; identity = $Envelope.identity; verb = $verb; required = $requiredCap }
        }
    }

    Update-IdentityState -Identity $Envelope.identity -Result "SUCCESS"

    # Phase 7.1 Security Mitigation: Force Shared Secret identities to PROPOSAL_ONLY (Tier 0)
    $effectiveTier = $idRecord.tier
    if ($idRecord.crypto_mode -eq "DEV_SHARED_SECRET") {
        $effectiveTier = 0
    }

    return @{
        ok              = $true
        identity        = $Envelope.identity
        tier            = $effectiveTier
        verified_intent = $intentObj
        intent_json     = $intentJson
    }
}

Export-ModuleMember -Function Test-IntentEnvelope
