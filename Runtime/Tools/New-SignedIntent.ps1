function New-SignedIntent {
    param(
        [Parameter(Mandatory = $true)][object]$Intent,
        [string]$Identity = "portal:maya_phone",
        [string]$Secret = "axis_dev_secret_001",
        [switch]$AsJson
    )

    $ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ") # Standard ISO 8601
    $nonce = [Guid]::NewGuid().ToString()

    # Canonical Intent JSON (Matches T08_EnvelopeVerifier expectation)
    # Note: PowerShell's ConvertTo-Json might differ slightly from Node/JS in spacing,
    # but as long as THIS string is what is signed and sent, it works.
    $intentJson = $Intent | ConvertTo-Json -Depth 20 -Compress

    # Canonical Payload for Signing
    # Format: ts|nonce|identity|intent_json
    $payload = "${ts}|${nonce}|${Identity}|${intentJson}"

    # HMAC-SHA256
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($Secret))
    $hashBytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($payload))
    $signatureHex = ([System.BitConverter]::ToString($hashBytes) -replace "-", "").ToLower()
    $signature = "hmac256:" + $signatureHex

    $envelope = [ordered]@{
        schema      = "axis.intent_envelope.v0.1"
        ts_utc      = $ts
        nonce       = $nonce
        identity    = $Identity
        intent_json = $intentJson
        intent      = $Intent # Legacy mirror
        signature   = $signature
    }

    if ($AsJson) {
        return $envelope | ConvertTo-Json -Depth 20 -Compress
    }
    return [pscustomobject]$envelope
}

# Export-ModuleMember removed for script usage
