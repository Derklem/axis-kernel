# Debug-RuntimeHashes.ps1
$RuntimeFile = "D:\Infinite\Infinity\Governance\decision_policy.json"
$LedgerHead = "ab41c483d8396cb6d37299541a" # Truncated but I'll use full if I have it

function Compute-Sha256([string]$s) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
    $hash = $sha.ComputeHash($bytes)
    return ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

$raw = Get-Content $RuntimeFile -Raw -Encoding UTF8
$rawHash = Compute-Sha256 $raw
Write-Host "Raw File Hash: $rawHash"

$obj = $raw | ConvertFrom-Json
$comp = $obj | ConvertTo-Json -Depth 10 -Compress
$compHash = Compute-Sha256 $comp
Write-Host "Comp Json Hash: $compHash"

$ledgerFull = (Get-Content D:\Infinite\Infinity\Governance\policy_update_ledger_v2.jsonl | ConvertFrom-Json).new_policy_hash
Write-Host "Ledger Head:   $ledgerFull"

if ($rawHash -eq $ledgerFull) { Write-Host "MATCH: RAW" -ForegroundColor Green }
if ($compHash -eq $ledgerFull) { Write-Host "MATCH: COMP" -ForegroundColor Green }
