<#
.SYNOPSIS
  T08 Envelope Verifier v1.0 (Hardened)
.DESCRIPTION
  Verifies Axis intent envelopes. Supports v0.1 (Legacy) and v1 (Hardened).
  Uses T09_KeyRing for secret retrieval.
#>

$script:RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$script:DecLog = Join-Path $script:RuntimeDir "decision_log.jsonl"
$script:RegistryPath = "D:\Infinite\Infinity\Truth_Engine\identity_registry.json"
$script:NonceCache = Join-Path $script:RuntimeDir "nonce_cache.jsonl"

function Get-IdentityRegistry {
    if (-not (Test-Path $script:RegistryPath)) { return $null }
    try { return (Get-Content $script:RegistryPath -Raw | ConvertFrom-Json) } catch { return $null }
}

function Get-IdentitySecret {
    param(
        [string]$identity,
        [string]$keyId = $null
    )
    $r = Get-IdentityRegistry
    if (-not $r -or -not $r.identities) { return $null }
    $signer = $r.identities | Where-Object { $_.identity -eq $identity -and ($_.status -eq "active" -or $_.enabled -eq $true) } | Select-Object -First 1
    if (-not $signer) { return $null }
    
    # Binding Check: If key_id is provided, it must match the signer record
    if ($keyId -and $signer.key_id -and $signer.key_id -ne $keyId) {
        Write-Warning "KeyID Mismatch for $identity. Expected $($signer.key_id), got $keyId."
        return $null
    }

    if ($signer.key_ref) {
        if (-not (Get-Module T09_KeyRing)) { Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1 -Force }
        return Get-AxisSecret -KeyRef $signer.key_ref
    }
    return $signer.secret # Fallback for legacy
}

function Normalize-Hex([string]$hex) {
    if (-not $hex) { return $null }
    return ($hex.Trim().ToLower() -replace '[^0-9a-f]', '')
}

function Compute-HmacSha256Hex($secret, $payload) {
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
    param(
        [Parameter(Mandatory = $true)] $Envelope,
        [int]$MaxSkewSeconds = 300
    )
    $res = [ordered]@{ ok = $false; reason = "unspecified"; identity = $null; intent_json = $null; intent_obj = $null }
    try {
        if (-not $Envelope) { $res.reason = "missing_envelope"; return [pscustomobject]$res }
        
        $schema = [string]$Envelope.schema
        if ($schema -notmatch "^axis\.intent_envelope\.v(0\.1|1|2)$") { 
            Write-Host "DEBUG: bad_schema. Got '$schema' (Length: $($schema.Length))." -ForegroundColor Yellow
            $res.reason = "bad_schema ($schema)"
            return [pscustomobject]$res 
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

        # Schema-specific payload construction
        $payload = if ($schema -eq "axis.intent_envelope.v2") {
            if ([string]::IsNullOrWhiteSpace($keyId)) { $res.reason = "missing_key_id_v2"; return [pscustomobject]$res }
            "$ts|$nonce|$identity|$keyId|$intentJson"
        }
        else {
            "$ts|$nonce|$identity|$intentJson"
        }

        $secret = Get-IdentitySecret -identity $identity -keyId $keyId
        if (-not $secret) { $res.reason = "unknown_or_disabled_identity_or_key_mismatch"; return [pscustomobject]$res }

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

Export-ModuleMember -Function Test-IntentEnvelope
