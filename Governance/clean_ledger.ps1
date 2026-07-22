$ledgerPath = 'D:\Infinite\Infinity\Governance\policy_update_ledger_v2.jsonl'
Write-Host "Cleaning $ledgerPath..."

$lines = Get-Content $ledgerPath
$validEntries = @()

foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
        $obj = $line | ConvertFrom-Json
        $validEntries += ($obj | ConvertTo-Json -Compress)
    }
    catch {
        Write-Warning "Skipping invalid line: '$line'"
    }
}

if ($validEntries.Count -gt 0) {
    $validEntries | Set-Content $ledgerPath -Encoding UTF8
    Write-Host "Ledger cleaned. $($validEntries.Count) entries preserved."
}
else {
    Write-Error "No valid entries found! Aborting rewrite."
}
