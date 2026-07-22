$ledgerPath = 'D:\Infinite\Infinity\Governance\policy_update_ledger_v2.jsonl'
try {
    Write-Host "Reading last line..."
    $lines = Get-Content $ledgerPath
    $headLine = $lines[-1]
    Write-Host "Line Length: $($headLine.Length)"
    Write-Host "Line Content: '$headLine'"
    
    Write-Host "Parsing Entry..."
    $headEntry = $headLine | ConvertFrom-Json
    
    Write-Host "Parsing Proof..."
    $proofStr = $headEntry.constraints_proof_json
    Write-Host "Proof String Length: $($proofStr.Length)"
    
    $storedProof = $proofStr | ConvertFrom-Json
    Write-Host "Success! Schema: $($storedProof.schema)"
}
catch {
    Write-Host "FAIL: $_"
    Write-Host "Exception Type: $($_.Exception.GetType().FullName)"
}
