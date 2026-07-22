param(
    [string]$Root = "D:\Infinite\Infinity"
)

$GovDir = Join-Path $Root "Governance"
$LedgerFile = Join-Path $GovDir "policy_update_ledger.jsonl"
$SourceFile = Join-Path $GovDir "Constitutional_Constraints.json"
$RuntimeFile = Join-Path $GovDir "decision_policy.json"

function Compute-Sha256([string]$s) {
    if ([string]::IsNullOrEmpty($s)) { return "" }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
    $hash = $sha.ComputeHash($bytes)
    return ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

# 1. Compile Genesis State
$sourceContent = Get-Content $SourceFile -Raw
$sourceJson = $sourceContent | ConvertFrom-Json

$compiledObject = [ordered]@{
    meta   = [ordered]@{
        compiled_ts  = (Get-Date).ToUniversalTime().ToString("o")
        compiler_ver = "v0.1"
        source_hash  = (Compute-Sha256 $sourceContent)
    }
    policy = $sourceJson
}

$compiledJsonOriginal = $compiledObject | ConvertTo-Json -Depth 10 -Compress
# Canonicalize
$jsonObj = $compiledJsonOriginal | ConvertFrom-Json
$compiledJson = $jsonObj | ConvertTo-Json -Depth 10 -Compress
$compiledHash = Compute-Sha256 $compiledJson

# 2. Create Genesis Block
# Phase 25: Include simple proof object for schema compatibility
$proof = [ordered]@{
    # ts removed
    policy_hash = $compiledHash
    checks      = @()
    result      = "PASS" # Genesis is axiomatic
}
$proofJson = $proof | ConvertTo-Json -Depth 10 -Compress

$genesis = [ordered]@{
    update_id              = "GENESIS"
    parent_hash            = "0000000000000000000000000000000000000000000000000000000000000000"
    new_policy_hash        = $compiledHash
    diff_summary           = "Genesis Policy Block"
    ts                     = (Get-Date).ToUniversalTime().ToString("o")
    signature              = "hmac256:GENESIS_SIG"
    constraints_proof_json = $proofJson
}

$genesisJson = $genesis | ConvertTo-Json -Depth 10 -Compress
[System.IO.File]::WriteAllText($LedgerFile, $genesisJson + "`n", [System.Text.Encoding]::UTF8)

# 3. Update Runtime File matches Genesis
[System.IO.File]::WriteAllText($RuntimeFile, $compiledJson, [System.Text.Encoding]::UTF8)

Write-Host "Ledger Reset to GENESIS." -ForegroundColor Green
Write-Host "Genesis Hash: $compiledHash"
