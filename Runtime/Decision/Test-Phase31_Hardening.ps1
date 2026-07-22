# Test-Phase31_Hardening.ps1
# Verifies:
# 1. Nonce Consistency (ID stays as nonce)
# 2. Unmapped Op Blocking
# 3. Wildcard Precedence (Exact > Longest Prefix)

Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1

function Sign-TestIntent {
    param(
        [string]$identity,
        [string]$op,
        [string]$nonce,
        [int]$version = 1
    )
    $intent = [ordered]@{
        intent_id      = "inner_id_to_be_ignored"
        correlation_id = "corr_123"
        op             = $op
        target         = "test:target"
        ts             = (Get-Date).ToUniversalTime().ToString("o")
    }
    $intentJson = $intent | ConvertTo-Json -Compress
    
    $reg = Get-Content D:\Infinite\Infinity\Truth_Engine\identity_registry.json -Raw | ConvertFrom-Json
    $signer = $reg.identities | Where-Object { $_.identity -eq $identity } | Select-Object -First 1
    if (-not $signer) { throw "Signer not found: $identity" }
    
    $envelope = [ordered]@{
        schema      = "axis.intent_envelope.v$version"
        identity    = $identity
        nonce       = $nonce
        ts_utc      = $intent.ts
        key_id      = if ($version -eq 2) { $signer.key_id } else { $null }
        intent_json = $intentJson
        signature   = ""
    }
    
    if ($envelope.schema -eq "axis.intent_envelope.v2" -and -not $envelope.key_id) {
        throw "v2 Envelope requires key_id for $identity"
    }

    $secret = Get-AxisSecret -KeyRef $signer.key_ref
    if (-not $secret) { throw "Secret not found for key_ref: $($signer.key_ref)" }
    
    # Payload Construction
    $sigPayload = if ($version -eq 2) {
        "$($envelope.ts_utc)|$($envelope.nonce)|$($envelope.identity)|$($envelope.key_id)|$($envelope.intent_json)"
    }
    else {
        "$($envelope.ts_utc)|$($envelope.nonce)|$($envelope.identity)|$($envelope.intent_json)"
    }
    
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($secret))
    $sigBytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($sigPayload))
    $envelope.signature = "hmac256:" + (($sigBytes | ForEach-Object { $_.ToString("x2") }) -join "")
    
    return $envelope
}

function Run-Test {
    param(
        [string]$name,
        [string]$identity,
        [string]$op,
        [string]$nonce,
        [int]$version = 1
    )
    Write-Host "`n>>> TEST: $name" -ForegroundColor Cyan
    try {
        $env = Sign-TestIntent -identity $identity -op $op -nonce $nonce -version $version
        $envJson = $env | ConvertTo-Json -Compress
        
        # Inject directly into queue (overwrite for test)
        $envJson | Set-Content D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl
        
        # Reset cursor to start
        $cursor = [ordered]@{ schema = "axis.queue_cursor.v0.1"; byte_offset = 0; line = 0; ts_utc = (Get-Date).ToUniversalTime().ToString("o") }
        $cursor | ConvertTo-Json | Set-Content D:\Infinite\Infinity\Runtime\Decision\intent_queue_cursor.json
        
        # Reset execution state to prevent dedupe skips
        $state = [ordered]@{
            executed_intents = @()
            failed_intents   = @()
            inflight         = @{}
            last_run_ts      = (Get-Date).ToUniversalTime().ToString("o")
        }
        $state | ConvertTo-Json | Set-Content D:\Infinite\Infinity\Runtime\Decision\execution_state.json
        
        # Run Executor (one cycle)
        $out = powershell -File D:\Infinite\Infinity\Runtime\Decision\T08_Executor.ps1 2>&1
        if ($out -match "FATAL" -or $out -match "ERROR") {
            Write-Host "EXECUTOR OUTPUT:`n$out" -ForegroundColor Gray
        }
        
        # Audit log (only look at tail for performance)
        $logs = Get-Content D:\Infinite\Infinity\Runtime\Decision\decision_log.jsonl -Tail 100 | ForEach-Object { 
            if ([string]::IsNullOrWhiteSpace($_)) { return $null }
            try { return $_ | ConvertFrom-Json } catch { return $null }
        } | Where-Object { $null -ne $_ }
        
        $found = $logs | Where-Object { $_.intent_id -eq $nonce }
        if (-not $found) {
            Write-Host "DEBUG: No log found for nonce '$nonce'. Found nonces: $( ($logs.intent_id | Where-Object {$_}) -join ', ' )" -ForegroundColor Yellow
        }
        return $found | Select-Object -Last 1
    }
    catch {
        Write-Host "ERROR running test '$name': $_" -ForegroundColor Red
        return $null
    }
}

# 1. Unmapped Op Test
$log1 = Run-Test -name "Unmapped Op" -identity "system:tester" -op "unknown:op" -nonce "nonce_unmapped"
if ($log1 -and $log1.result -eq "BLOCKED_CAPABILITY_UNMAPPED") { Write-Host "[PASS] Unmapped op blocked correctly." -ForegroundColor Green }
else { Write-Host "[FAIL] Unmapped op result: $(if($log1){$log1.result}else{'NOT_FOUND'})" -ForegroundColor Red }

# 2. Wildcard Match (Success)
$log2 = Run-Test -name "Wildcard Match (Normal)" -identity "system:tester" -op "tool:execute:safe_tool" -nonce "nonce_wildcard"
if ($log2 -and ($log2.result -eq "EXECUTION_COMPLETE" -or $log2.result -eq "DISPATCH_SUCCESS")) { Write-Host "[PASS] Generic tool match allowed." -ForegroundColor Green }
else { Write-Host "[FAIL] Generic tool match result: $(if($log2){$log2.result}else{'NOT_FOUND'})" -ForegroundColor Red }

# 3. Wildcard Precedence (Failure - Stricter Exact Match)
# system:tester has "tool.execute" but NOT "high.risk"
$log3 = Run-Test -name "Wildcard Precedence" -identity "system:tester" -op "tool:execute:strictest" -nonce "nonce_precedence"
if ($log3 -and $log3.result -eq "BLOCKED_CAPABILITY" -and $log3.message -match "high.risk") { Write-Host "[PASS] Stricter exact match correctly blocked precedence-based bypass." -ForegroundColor Green }
else { Write-Host "[FAIL] Precedence test result: $(if($log3){$log3.result}else{'NOT_FOUND'}) / $(if($log3){$log3.message}else{'---'})" -ForegroundColor Red }

# 4. ID Consistency Test
if ($log3 -and $log3.intent_id -eq "nonce_precedence") { Write-Host "[PASS] ID consistency maintained (Canonical=Nonce)." -ForegroundColor Green }
else { Write-Host "[FAIL] ID corrupted or missing for 'nonce_precedence'." -ForegroundColor Red }
