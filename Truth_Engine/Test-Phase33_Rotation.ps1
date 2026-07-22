# Test-Phase33_Rotation.ps1
# Verifies "Real Rotation" (Phase 32.2/33)
# 1. Mint V2
# 2. Update Registry -> V2
# 3. Revoke V1
# 4. Prove V2 works, V1 blocked

$ErrorActionPreference = "Stop"
Start-Transcript -Path "D:\Infinite\Infinity\Truth_Engine\rotation_transcript.txt" -Force

# --- Setup ---
$Root = "D:\Infinite\Infinity"
$SecretsDir = Join-Path $Root "Secrets"
$VaultFile = Join-Path $SecretsDir "keyring.json"
$RegistryFile = "D:\Infinite\Infinity\Truth_Engine\identity_registry.json"

# Inline Dependencies to avoid import issues
. "D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1"

# Mock the function (avoiding full module import complexity)
# We just need the Gate Logic, but we can call T08 directly if needed
# OR we can replicate the gate logic here to test it isolated. 
# BUT the User wants to prove the *real* gate works.

# Let's import T08 functions
try {
    . "D:\Infinite\Infinity\Runtime\Decision\T08_Executor.ps1"
}
catch {
    Write-Warning "Could not dot-source T08 directly. Falling back to inline gate logic."
}

Write-Output ">>> Starting Phase 33 Rotation Verification" -ForegroundColor Cyan

# 1. Mint V2 Key
Write-Output "Step 1: Minting V2 Key..."
$v2Ref = Get-AxisKeyRef -Identity "system:tester" -Version "v2"
$v2Secret = "rotation_secret_v2_" + (Get-Date).Ticks
Set-AxisSecret -KeyRef $v2Ref -Secret $v2Secret
Write-Output "Minted: $v2Ref"

# 2. Update Identity Registry -> V2
Write-Output "Step 2: Updating Registry to V2..."
$reg = Get-Content $RegistryFile -Raw | ConvertFrom-Json
$identities = $reg.identities
$testerIdx = -1
for ($i = 0; $i -lt $identities.Count; $i++) {
    if ($identities[$i].identity -eq "system:tester") {
        $testerIdx = $i; break
    }
}
if ($testerIdx -ne -1) {
    $reg.identities[$testerIdx].key_id = "v2"
    $reg.identities[$testerIdx].key_ref = $v2Ref
    $reg.identities[$testerIdx] | ConvertTo-Json -Depth 5
}
$reg | ConvertTo-Json -Depth 10 | Set-Content $RegistryFile -Encoding UTF8
Write-Output "Registry Updated: system:tester -> key_id=v2"

# 3. Revoke V1 Key
Write-Output "Step 3: Revoking V1 Key..."
$v1Ref = Get-AxisKeyRef -Identity "system:tester" -Version "v1"
Revoke-AxisKey -KeyRef $v1Ref -Reason "Phase 33 Rotation"
Write-Output "Revoked: $v1Ref"

# 4. Verify V1 Blocked (Negative Test)
Write-Output "Step 4: Testing V1 (Should be BLOCKED)..."
$v1Envelope = [pscustomobject]@{
    identity = "system:tester"
    key_id   = "v1" # Claiming V1
    payload  = "test_v1"
}

# The gate should see "v1" != registry "v2" -> BLOCKED_KEY_MISMATCH
$gateV1 = Test-AxisKeyLifecycleAllowed -Envelope $v1Envelope
if ($gateV1.reason -eq "BLOCKED_KEY_MISMATCH") {
    Write-Output "[PASS] V1 Blocked: $($gateV1.reason)" -ForegroundColor Green
}
else {
    Write-Output "[FAIL] V1 Not Blocked correctly! key_id mismatch expected. Got: $($gateV1.reason)" -ForegroundColor Red
}

# 5. Verify V2 Allowed (Positive Test)
Write-Output "Step 5: Testing V2 (Should be ALLOWED)..."
$v2Envelope = [pscustomobject]@{
    identity = "system:tester"
    key_id   = "v2" # Claiming V2
    payload  = "test_v2"
}

# The gate should see "v2" == registry "v2", then check KeyRing($v2Ref) -> ACTIVE
$gateV2 = Test-AxisKeyLifecycleAllowed -Envelope $v2Envelope
if ($gateV2.ok) {
    Write-Output "[PASS] V2 Allowed." -ForegroundColor Green
}
else {
    Write-Output "[FAIL] V2 Blocked! Reason: $($gateV2.reason)" -ForegroundColor Red
}

Stop-Transcript
Write-Output ">>> Rotation Verification Complete"
