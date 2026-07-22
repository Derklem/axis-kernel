# Manual-Test-Executor.ps1
Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1

function Sign-TestIntent {
    param($identity, $op, $nonce)
    $intent = [ordered]@{
        intent_id      = "inner_id"
        correlation_id = "corr_manual"
        op             = $op
        target         = "test:target"
        ts             = (Get-Date).ToUniversalTime().ToString("o")
    }
    $intentJson = $intent | ConvertTo-Json -Compress
    
    $envelope = [ordered]@{
        schema      = "axis.intent_envelope.v1"
        identity    = $identity
        nonce       = $nonce
        ts_utc      = $intent.ts
        intent_json = $intentJson
        signature   = ""
    }
    
    $reg = Get-Content D:\Infinite\Infinity\Truth_Engine\identity_registry.json -Raw | ConvertFrom-Json
    $signer = $reg.identities | Where-Object { $_.identity -eq $identity } | Select-Object -First 1
    $secret = Get-AxisSecret -KeyRef $signer.key_ref
    
    $sigPayload = "$($envelope.ts_utc)|$($envelope.nonce)|$($envelope.identity)|$($envelope.intent_json)"
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($secret))
    $sigBytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($sigPayload))
    $envelope.signature = "hmac256:" + (($sigBytes | ForEach-Object { $_.ToString("x2") }) -join "")
    return $envelope
}

$env = Sign-TestIntent -identity 'system:tester' -op 'unknown:op' -nonce 'manual_test_nonce'
$env | ConvertTo-Json -Compress | Set-Content D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl

# Reset cursor
$cursor = [ordered]@{ byte_offset = 0; line = 0; ts_utc = (Get-Date).ToUniversalTime().ToString("o") }
$cursor | ConvertTo-Json | Set-Content D:\Infinite\Infinity\Runtime\Decision\cursor_state.json

# Run Wrapper
powershell -File D:\Infinite\Infinity\Runtime\Decision\Run_T08.ps1
