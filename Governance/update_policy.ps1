$ledgerPath = 'D:\Infinite\Infinity\Governance\policy_update_ledger_v2.jsonl'
$policyPath = 'D:\Infinite\Infinity\Governance\decision_policy.json'

Write-Host "Reading Ledger Head..."
$head = Get-Content $ledgerPath -Tail 1 | ConvertFrom-Json
$hash = $head.new_policy_hash
Write-Host "New Hash: $hash"

Write-Host "Updating Policy..."
$policy = Get-Content $policyPath -Raw | ConvertFrom-Json
$oldHash = $policy.meta.source_hash
$policy.meta.source_hash = $hash

$json = $policy | ConvertTo-Json -Depth 10 -Compress
Set-Content $policyPath -Value $json -Encoding UTF8
Write-Host "Updated Policy Source Hash from $oldHash to $hash"
