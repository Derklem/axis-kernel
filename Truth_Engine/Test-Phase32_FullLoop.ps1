# Test-Phase32_FullLoop.ps1
# Full Lifecycle Verification: Sign -> Execute -> Revoke -> Block

. "D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1"
$Verifier = "D:\Infinite\Infinity\Truth_Engine\T08_EnvelopeVerifier.psm1"
Import-Module $Verifier -Force

$RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$QueueFile = Join-Path $RuntimeDir "intent_queue.jsonl"
$CursorFile = Join-Path $RuntimeDir "intent_queue_cursor.json"
$DecLog = Join-Path $RuntimeDir "decision_log.jsonl"

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

Write-Host ">>> Starting Phase 32 Full Loop Verification" -ForegroundColor Cyan

# 1. Reset Environment
Write-Host "Step 1: Resetting Environment & Key State"
$cursor = [ordered]@{ schema = "axis.queue_cursor.v0.1"; byte_offset = 0; line = 0; ts_utc = (Get-Date).ToUniversalTime().ToString("o") }
$cursor | ConvertTo-Json | Set-Content $CursorFile
"" | Set-Content $QueueFile

# Force Reset Key Status to ACTIVE
$vaultFile = "D:\Infinite\Infinity\Secrets\keyring.json"
$vault = Get-Content $vaultFile -Raw | ConvertFrom-Json
if ($vault.keys.'dpapi:CURRENTUSER:axis:system_tester:v1') {
    $vault.keys.'dpapi:CURRENTUSER:axis:system_tester:v1'.status = "ACTIVE"
    $vault | ConvertTo-Json -Depth 10 | Set-Content $vaultFile -Encoding UTF8
}

# 2. Positive Test (Active Key)
Write-Host "Step 2: Testing Active Key"
$env1 = Sign-V2 -identity "system:tester" -op "noop:heartbeat" -nonce "phase32_pos_001"
$env1 | ConvertTo-Json -Compress | Set-Content $QueueFile
powershell -File D:\Infinite\Infinity\Runtime\Decision\Run_T08.ps1

$log = Get-Content $DecLog -Tail 5
if ($log -match "LIFECYCLE_GATE_PASS") { 
    Write-Host "[PASS] Active Key Authorized" -ForegroundColor Green 
}
else { 
    Write-Error "Step 2 Failed. Log: $log" 
}

# 3. Revoke Key
Write-Host "Step 3: Revoking system:tester Key (Simulating Compromise)"
# Capture secret BEFORE revocation for negative test (Simulating stolen key)
$targetKeyRef = "dpapi:CURRENTUSER:axis:system_tester:v1"
$stolenSecret = Get-AxisSecret -KeyRef $targetKeyRef
if (-not $stolenSecret) { Write-Error "Failed to capture secret for negative test."; exit }

Revoke-AxisKey -KeyRef $targetKeyRef -Reason "FullLoop Verification"
# Record in Ledger
$ledgerBlock = [ordered]@{
    schema  = "axis.key_ledger.v1"
    ts      = (Get-Date).ToUniversalTime().ToString("o")
    id      = [Guid]::NewGuid().ToString()
    type    = "REVOKE"
    key_id  = "k_system_tester_v1"
    status  = "REVOKED"
    message = "Revoked via FullLoop Verification"
}
$ledgerBlock | ConvertTo-Json -Compress | Add-Content D:\Infinite\Infinity\Governance\key_ledger.jsonl

# 4. Negative Test (Revoked Key)
Write-Host "Step 4: Testing Revoked Key (Using Stolen Secret)"
$env2 = Sign-V2 -identity "system:tester" -op "noop:heartbeat" -nonce "phase32_neg_002" -forceSecret $stolenSecret
$env2 | ConvertTo-Json -Compress | Set-Content $QueueFile # Overwrite
# Reset cursor again for the new intent
$cursor | ConvertTo-Json | Set-Content $CursorFile

powershell -File D:\Infinite\Infinity\Runtime\Decision\Run_T08.ps1

$log = Get-Content $DecLog -Tail 5
if ($log -match "BLOCKED_KEY_KEY_REVOKED") { 
    Write-Host "[PASS] Revoked Key Blocked" -ForegroundColor Green 
}
else { 
    Write-Error "Step 4 Failed. Log: $log" 
}

# 5. Restore for cleanup
Write-Host "Step 5: Restoring Key for next tests (Cleanup)"
$vaultFile = "D:\Infinite\Infinity\Secrets\keyring.json"
$vault = Get-Content $vaultFile -Raw | ConvertFrom-Json
$vault.keys.'dpapi:CURRENTUSER:axis:system_tester:v1'.status = "ACTIVE"
$vault | ConvertTo-Json -Depth 10 | Set-Content $vaultFile -Encoding UTF8

Write-Host "`n>>> Full Loop Verification Complete" -ForegroundColor Cyan
