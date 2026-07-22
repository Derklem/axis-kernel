# Axis_Build_Genesis_v2.ps1
# Generates the Genesis Block for the v2 Policy Ledger (Hardened)

$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$LedgerPath = Join-Path $GovDir "policy_update_ledger.jsonl"
$SourcePath = Join-Path $GovDir "genesis_policy_source.json"
$RuntimePath = Join-Path $GovDir "decision_policy.json"
$IdentityFile = Join-Path $Root "Truth_Engine\identity_registry.json"

Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1

# 1. Load Identity (Need a signer)
$reg = Get-Content $IdentityFile -Raw | ConvertFrom-Json
$signerEntry = $reg.identities | Where-Object { $_.status -eq "active" -and ($_.capabilities -contains "policy.compile" -or $_.capabilities -contains "*") } | Select-Object -First 1

if (-not $signerEntry) {
    Write-Error "No authorized signer found for Genesis."
    exit 1
}

$secret = Get-AxisSecret -KeyRef $signerEntry.key_ref
if (-not $secret) {
    Write-Error "Could not retrieve secret for $($signerEntry.identity) from KeyRing."
    exit 1
}

Write-Host "Signer: $($signerEntry.identity) (via KeyRing)"

# 2. Compute Source Hash
if (-not (Test-Path $SourcePath)) {
    # Create default source if missing
    $defaultSource = [ordered]@{
        revision           = "GENESIS"
        intent_constraints = @()
        promotion_criteria = @()
    }
    $defaultSource | ConvertTo-Json -Depth 5 | Set-Content $SourcePath -Encoding UTF8
}

$rawSource = Get-Content $SourcePath -Raw -Encoding UTF8
function Compute-Sha256([string]$s) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
    return ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Hmac256($key, $msg) {
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($key))
    return ($hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($msg)) | ForEach-Object { $_.ToString("x2") }) -join ""
}

$sourceHash = Compute-Sha256 $rawSource
Write-Host "Source Hash: $sourceHash"

# 3. Construct Policy Object
$sourceObj = $rawSource | ConvertFrom-Json
$compiledGen = [ordered]@{
    meta   = [ordered]@{
        compiled_ts  = "GENESIS"
        compiler_ver = "v0.1"
        source_hash  = $sourceHash
    }
    policy = $sourceObj
}
$compiledJson = $compiledGen | ConvertTo-Json -Depth 10 -Compress
$policyHash = Compute-Sha256 $compiledJson
Write-Host "Policy Hash: $policyHash"

# 4. Generate Proof
# We use the real probe for Genesis now
$ProbeScript = Join-Path $GovDir "Axis_Test_PolicyConstraints.ps1"
if (-not (Test-Path $ProbeScript)) { Write-Error "Probe script missing"; exit 1 }
Set-Content -Path ($RuntimePath + ".tmp") -Value $compiledJson -Encoding UTF8
$proofObj = & $ProbeScript -PolicyPath ($RuntimePath + ".tmp") | ConvertFrom-Json
Remove-Item ($RuntimePath + ".tmp") -Force

if ($proofObj.result -ne "PASS") { Write-Error "Genesis constraints check failed!"; exit 1 }

# 5. Build Ledger Entry
$entry = [ordered]@{
    update_id              = "GENESIS"
    ts                     = (Get-Date).ToString("yyyy-MM-ddTHH:mm:ssZ")
    signer                 = $signerEntry.identity
    sig_alg                = "hmac256"
    key_id                 = $signerEntry.key_id
    parent_hash            = "0000000000000000000000000000000000000000000000000000000000000000"
    new_policy_hash        = $policyHash
    diff_summary           = "GENESIS_BLOCK"
    schema                 = "axis.policy_ledger_entry.v2"
    genesis_source_path    = "Governance\genesis_policy_source.json"
    genesis_source_hash    = $sourceHash
    constraints_proof_json = ($proofObj | ConvertTo-Json -Compress)
    signature              = ""
}

# 6. Sign
# Deterministic Subset for Proof Hash
$pHashObj = [ordered]@{ schema = $proofObj.schema; policy_hash = $proofObj.policy_hash; checked = $proofObj.checked; result = $proofObj.result }
$pJson = $pHashObj | ConvertTo-Json -Depth 10 -Compress
$pHash = Compute-Sha256 $pJson

$sigPayload = "$($entry.ts)|$($entry.update_id)|$($entry.parent_hash)|$($entry.new_policy_hash)|$($entry.diff_summary)|$($entry.genesis_source_hash)|$pHash"
$entry.signature = "hmac256:" + (Hmac256 $secret $sigPayload)

# 7. Write Ledger
$jsonLine = $entry | ConvertTo-Json -Compress
$jsonLine | Set-Content $LedgerPath -Encoding UTF8

# 8. Update Runtime Policy
$compiledJson | Set-Content $RuntimePath -Encoding UTF8

Write-Host "Genesis Rebuilt (v2 Phase 30)."
Write-Host "   Ledger: $LedgerPath"
Write-Host "   Policy: $RuntimePath"
