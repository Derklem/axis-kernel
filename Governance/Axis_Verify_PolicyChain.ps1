[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity",
    [string]$LedgerPath = $null,
    [switch]$VerifyRuntime
)

$ErrorActionPreference = "Stop"

# Paths
$GovDir = Join-Path $Root "Governance"
$ManifestFile = Join-Path $GovDir "state_vector_manifest.json"
$Manifest = Get-Content $ManifestFile | ConvertFrom-Json

$LedgerFile = if ($LedgerPath) { $LedgerPath } else { Join-Path $Root $Manifest.components.policy.path }
$RuntimeFile = Join-Path $GovDir "decision_policy.json"
$IdentityFile = Join-Path $Root $Manifest.components.identity.path

Import-Module (Join-Path $Root "Truth_Engine\T09_KeyRing.psm1")

Write-Host "--- Axis Policy Chain Verifier (v2.2 Phase 30) ---" -ForegroundColor Cyan

# Hash Standardization (Hard Rule: sha256:<hex>)
function Compute-Sha256([string]$s, [switch]$Prefix) {
    if ([string]::IsNullOrEmpty($s)) { return "" }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
    $hex = ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""
    if ($Prefix) { return "sha256:$hex" } else { return $hex }
}

function Hmac256($key, $msg) {
    if ([string]::IsNullOrEmpty($key)) { throw "Missing Key for HMAC" }
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($key))
    $hash = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($msg))
    return ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

# 1. Load Data
if (-not (Test-Path $IdentityFile)) { Write-Host "[FAIL] Identity Registry Missing at $IdentityFile" -ForegroundColor Red; exit 1 }
$reg = Get-Content $IdentityFile -Raw | ConvertFrom-Json

if (-not (Test-Path $LedgerFile)) { Write-Host "[FAIL] Ledger Missing: $LedgerFile" -ForegroundColor Red; exit 1 }
$ledger = @()
try {
    $lines = Get-Content $LedgerFile
    foreach ($line in $lines) {
        if (-not [string]::IsNullOrWhiteSpace($line)) { $ledger += ($line | ConvertFrom-Json) }
    }
}
catch { Write-Host "[FAIL] Ledger Parse Error: $_" -ForegroundColor Red; exit 1 }

if ($ledger.Count -eq 0) { Write-Host "[WARN] Ledger empty." -ForegroundColor Yellow; exit 0 }

# 2. Iterative Verification
$lastHash = "genesis"
$lastTs = $null
$seenIds = [System.Collections.Generic.HashSet[string]]::new()
$idx = 0

foreach ($entry in $ledger) {
    $idx++
    
    # A. Continuity & Replay
    $pHash = if ($entry.parent_hash) { $entry.parent_hash } else { $entry.previous_hash }
    if ($pHash -ne $lastHash) {
        Write-Host "[FAIL] Chain Break at #$idx. Expected $lastHash, Got $pHash" -ForegroundColor Red
        exit 1
    }
    if ($seenIds.Contains($entry.update_id)) { 
        Write-Host "[FAIL] Replay at #$idx" -ForegroundColor Red; exit 1 
    }
    $seenIds.Add($entry.update_id) | Out-Null
    
    $tsRaw = if ($entry.ts) { $entry.ts } else { $entry.timestamp }
    $currTs = [DateTime]::Parse($tsRaw)
    if ($lastTs -and $currTs -lt $lastTs) { Write-Host "[FAIL] Time Violation at #$idx" -ForegroundColor Red; exit 1 }
    $lastTs = $currTs

    # B. Signature Verification (Phase 30: KeyId Aware)
    if ($entry.signer) {
        $signerEntry = $reg.identities | Where-Object { $_.identity -eq $entry.signer }
        if (-not $signerEntry) { Write-Host "[FAIL] Unknown Signer: $($entry.signer)" -ForegroundColor Red; exit 1 }
        
        # Capability check (Hardened)
        if ($signerEntry.capabilities -contains "*" -or $signerEntry.capabilities -contains "policy.compile") { }
        else { Write-Host "[FAIL] Signer '$($entry.signer)' lacks 'policy.compile' capabilities" -ForegroundColor Red; exit 1 }

        # Payload Construction
        $proofHash = ""
        try {
            $pObj = $entry.constraints_proof_json | ConvertFrom-Json
            if ($pObj.schema -eq "axis.policy_constraints_proof.v1") {
                $pHashObj = [ordered]@{ schema = $pObj.schema; policy_hash = $pObj.policy_hash; checked = $pObj.checked; result = $pObj.result }
                $proofHash = Compute-Sha256 ($pHashObj | ConvertTo-Json -Depth 10 -Compress)
            }
            else { $proofHash = Compute-Sha256 $entry.constraints_proof_json }
        }
        catch { $proofHash = Compute-Sha256 $entry.constraints_proof_json }

        $sigPayloadBase = "$($entry.ts)|$($entry.update_id)|$($entry.parent_hash)|$($entry.new_policy_hash)|$($entry.diff_summary)|"
        if ($entry.update_id -eq "GENESIS") { $sigPayloadBase += "$($entry.genesis_source_hash)|" }
        $sigPayloadWithProof = $sigPayloadBase + $proofHash
        $sigPayloadLegacy = $sigPayloadBase.TrimEnd('|')

        # Resolve Secret via KeyRing
        $keyRef = $signerEntry.key_ref
        
        # Phase 30: Strict KeyId Binding
        if ($entry.key_id -and $entry.key_id -ne $signerEntry.key_id) {
            Write-Host "[FAIL] KeyId Mismatch at #$idx! Entry requires $($entry.key_id), but signer current key is $($signerEntry.key_id)." -ForegroundColor Red
            exit 1
        }

        $secret = Get-AxisSecret -KeyRef $keyRef
        if (-not $secret) { Write-Host "[FAIL] Key not found in vault: $keyRef" -ForegroundColor Red; exit 1 }

        # Try Modern Payload first
        $calcSig = "hmac256:" + (Hmac256 $secret $sigPayloadWithProof)
        if ($calcSig -ne $entry.signature) {
            # Fallback to Legacy Payload
            $calcSig = "hmac256:" + (Hmac256 $secret $sigPayloadLegacy)
        }

        if ($calcSig -ne $entry.signature) {
            Write-Host "[FAIL] Signature Mismatch at #$idx ($($entry.update_id))" -ForegroundColor Red
            Write-Host "   Expected: $calcSig"
            Write-Host "   Got:      $($entry.signature)"
            exit 1
        }
    }
    
    $lastHash = $entry.new_policy_hash
}

Write-Host "[PASS] Chain Verified ($idx blocks)." -ForegroundColor Green

# 3. Runtime Binding
if ($VerifyRuntime) {
    Write-Host "Verifying Runtime Binding..."
    if (-not (Test-Path $RuntimeFile)) { Write-Host "[FAIL] Runtime Policy Missing" -ForegroundColor Red; exit 1 }
    
    # A. Content Hash Binding
    $runtimeRaw = Get-Content $RuntimeFile -Raw -Encoding UTF8
    $runtimeHash = Compute-Sha256 $runtimeRaw
    
    if ($runtimeHash -ne $lastHash -and "sha256:$runtimeHash" -ne $lastHash) {
        # Try compressed canonicalization fallback
        $runtimeObj = $runtimeRaw | ConvertFrom-Json
        $runtimeJson = $runtimeObj | ConvertTo-Json -Depth 10 -Compress
        $runtimeHash = Compute-Sha256 $runtimeJson
        
        if ($runtimeHash -ne $lastHash -and "sha256:$runtimeHash" -ne $lastHash) {
            Write-Host "[FAIL] Runtime Policy DIVERTED from Ledger Head!" -ForegroundColor Red
            Write-Host "   Head: $lastHash"
            Write-Host "   File: $runtimeHash"
            exit 1
        }
    }
    Write-Host "[PASS] Identity: Policy matches Ledger Head." -ForegroundColor Green

    # B. Invariant Check (Phase 25/26 Semantic Proof)
    $ProbeScript = Join-Path $GovDir "Axis_Test_PolicyConstraints.ps1"
    if (Test-Path $ProbeScript) {
        $freshProof = & $ProbeScript -PolicyPath $RuntimeFile | ConvertFrom-Json
        if ($freshProof.result -ne "PASS") { Write-Host "[FAIL] Runtime Policy fails invariants!" -ForegroundColor Red; exit 1 }
        
        if ($freshProof.policy_hash -ne $lastHash -and $freshProof.policy_hash -ne "sha256:$lastHash") {
            Write-Host "[FAIL] Runtime Proof targets wrong policy hash!" -ForegroundColor Red
            Write-Host "   Proof: $($freshProof.policy_hash)"
            Write-Host "   Actual: $lastHash"
            exit 1
        }
        Write-Host "Constitutional Invariants: PASS" -ForegroundColor Green
        Write-Host "Proof Semantics: VERIFIED" -ForegroundColor Green
    }
}

exit 0
