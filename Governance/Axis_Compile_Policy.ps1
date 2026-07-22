[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity",
    [string]$Identity = "portal:maya_phone",
    [string]$Reason = "Policy Update"
)

$ErrorActionPreference = "Stop"

# Paths
$GovDir = Join-Path $Root "Governance"
$SourceFile = Join-Path $GovDir "Constitutional_Constraints.json"
$RuntimeFile = Join-Path $GovDir "decision_policy.json"
$LedgerFile = Join-Path $GovDir "policy_update_ledger.jsonl"
$IdentityFile = Join-Path $Root "Truth_Engine\identity_registry.json"

# Helpers
function Compute-Sha256([string]$s) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
    $hash = $sha.ComputeHash($bytes)
    return ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Hmac256([string]$key, [string]$msg) {
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($key))
    $bytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($msg))
    return ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

# 1. Read Source
if (-not (Test-Path $SourceFile)) { throw "Source policy not found: $SourceFile" }
$sourceContent = Get-Content $SourceFile -Raw
$sourceJson = $sourceContent | ConvertFrom-Json

# 2. Compile/Normalize (Ordered for stability)
# Schema: meta + policy
$compiledObject = [ordered]@{
    meta   = [ordered]@{
        compiled_ts  = (Get-Date).ToUniversalTime().ToString("o")
        compiler_ver = "v0.1"
        source_hash  = (Compute-Sha256 $sourceContent)
    }
    policy = $sourceJson
}

# Serialize once to Object -> JSON String
$compiledJsonOriginal = $compiledObject | ConvertTo-Json -Depth 10 -Compress

# Re-parse and Re-serialize to guarantee canonical format matching Verifier
$jsonObj = $compiledJsonOriginal | ConvertFrom-Json
$compiledJson = $jsonObj | ConvertTo-Json -Depth 10 -Compress
$compiledHash = Compute-Sha256 $compiledJson

# 3. Get Parent Hash
$parentHash = "0000000000000000000000000000000000000000000000000000000000000000"
if (Test-Path $LedgerFile) {
    $last = Get-Content $LedgerFile -Tail 1 | ConvertFrom-Json
    if ($last.new_policy_hash) { $parentHash = $last.new_policy_hash }
}

# 4. Sign
if (-not (Test-Path $IdentityFile)) { throw "Identity registry missing" }
Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1
$reg = Get-Content $IdentityFile -Raw | ConvertFrom-Json
$signerEntry = $reg.identities | Where-Object { $_.identity -eq $Identity }
if (-not $signerEntry) { throw "Signer identity not found: $Identity" }

$secret = Get-AxisSecret -KeyRef $signerEntry.key_ref
if (-not $secret) { throw "Could not retrieve secret for $Identity from KeyRing" }

$ts = (Get-Date).ToUniversalTime().ToString("o")
$nonce = [Guid]::NewGuid().ToString()

# Sig: ts|nonce|parent|new|reason|proof_hash
# We bind the PROOF of constraints to the signature

try {
    # 4. Proof-on-Candidate (Phase 26)
    $CandidateFile = $RuntimeFile + ".candidate"
    [System.IO.File]::WriteAllText($CandidateFile, $compiledJson, [System.Text.Encoding]::UTF8)

    # Generate Dynamic Proof against CANDIDATE
    $ProbeScript = Join-Path $GovDir "Axis_Test_PolicyConstraints.ps1"
    
    try {
        $proofChk = & $ProbeScript -PolicyPath $CandidateFile | ConvertFrom-Json
    }
    catch {
        Remove-Item $CandidateFile -Force -ErrorAction SilentlyContinue
        throw "Proof Generation Failed: $_"
    }

    if ($proofChk.result -ne "PASS") {
        Remove-Item $CandidateFile -Force -ErrorAction SilentlyContinue
        throw "Constitutional Invariants Failed: $($proofChk | ConvertTo-Json -Depth 5)"
    }

    # Store as Canonical String to ensure Verify Hash matches Compile Hash
    # We must exclude the timestamp from the HASHED object to ensure determinism
    # The Probe returns ts_utc, but we strip it before hashing.
    $proofForHash = [ordered]@{
        schema      = $proofChk.schema
        policy_hash = $proofChk.policy_hash
        checked     = $proofChk.checked
        result      = $proofChk.result
    }
    
    $proofJson = $proofForHash | ConvertTo-Json -Depth 10 -Compress
    $proofHash = Compute-Sha256 $proofJson

    # Assert non-degenerate hash
    if ($proofHash -eq "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855") {
        throw "Proof Hash is Empty String (e3b0...) - ABORTING"
    }

    $sigPayload = "${ts}|${nonce}|${parentHash}|${compiledHash}|${Reason}|${proofHash}"
    $sig = Hmac256 $secret $sigPayload

    # 5. Ledger Entry
    $entry = [ordered]@{
        update_id              = $nonce
        ts                     = $ts
        parent_hash            = $parentHash
        new_policy_hash        = $compiledHash
        diff_summary           = $Reason
        signer                 = $Identity
        sig_alg                = "hmac256"
        key_id                 = $signerEntry.key_id
        signature              = "hmac256:$sig"
        constraints_proof_json = ($proofChk | ConvertTo-Json -Depth 10 -Compress) # Store full proof with TS
    }

    # 6. Commit (Ledger Append)
    $entryJson = $entry | ConvertTo-Json -Depth 10 -Compress
    [System.IO.File]::AppendAllText($LedgerFile, $entryJson + "`n", [System.Text.Encoding]::UTF8)

    # 7. Atomic Promotion (Candidate -> Runtime)
    Move-Item -Path $CandidateFile -Destination $RuntimeFile -Force

    Write-Host "Policy Compiled, Proved & Committed." -ForegroundColor Green
    Write-Host "  Update ID: $nonce"
    Write-Host "  New Hash:  $compiledHash"
    Write-Host "  Proof Hash: $proofHash"
}
catch {
    Write-Error "Compilation Failed: $_"
    # Cleanup candidate if it exists
    if (Test-Path ($RuntimeFile + ".candidate")) { 
        Remove-Item ($RuntimeFile + ".candidate") -Force -ErrorAction SilentlyContinue 
    }
    exit 1
}
