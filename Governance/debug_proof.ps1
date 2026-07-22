$ledgerPath = 'D:\Infinite\Infinity\Governance\policy_update_ledger_v2.jsonl'
$l = Get-Content $ledgerPath -Tail 1 | ConvertFrom-Json
if ($l.constraints_proof_json) {
    Write-Host "Reading last lines..."
    $lines = Get-Content $ledgerPath
    Write-Host "Total Lines: $($lines.Count)"
    
    $last = $lines[-1]
    Write-Host "Last Line ([-1]) Length: $($last.Length)"
    Write-Host "Last Line Content: '$last'"
    
    if ($lines.Count -gt 1) {
        $prev = $lines[-2]
        Write-Host "Prev Line ([-2]) Length: $($prev.Length)"
        Write-Host "Prev Line Content: '$prev'"
    }

    $headLine = $last
    $headEntry = $headLine | ConvertFrom-Json
    $proof = $headEntry.constraints_proof_json | ConvertFrom-Json
    
    Write-Host "-------------------------------------------"
    Write-Host "Proof Object Dump:"
    Write-Host ($proof | ConvertTo-Json -Depth 5)
    Write-Host "-------------------------------------------"
    
    if ($headEntry.new_policy_hash -eq $proof.policy_hash) {
        Write-Host "MATCH"
    }
    else {
        Write-Host "MISMATCH"
    }
}
else {
    Write-Host "Field is null or missing"
}
