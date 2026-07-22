$DecLog = "D:\Infinite\Infinity\Runtime\Decision\decision_log.jsonl"
$RecLog = "D:\Infinite\Infinity\Runtime\Receipts\Receipt_Ledger.jsonl"

Write-Host "Monitoring Campaign Logs... (Ctrl+C to stop)" -ForegroundColor Cyan

# Use Start-Job to monitor both files or just alternate
# Simple approach: Monitor Receipt Ledger mainly as it's the source of truth for 200 OK

Get-Content $RecLog -Wait -Tail 0 | ForEach-Object {
    $line = $_
    if ($line -match "ATTEMPT|RECEIPT") {
        try {
            $obj = $line | ConvertFrom-Json
            if ($obj.type -eq "ATTEMPT") {
                Write-Host "[$($obj.ts)] ATTEMPT -> $($obj.target)" -ForegroundColor Yellow
            }
            elseif ($obj.type -eq "RECEIPT") {
                $color = if ($obj.receipt.http_status -eq 200) { "Green" } else { "Red" }
                Write-Host "[$($obj.ts)] RECEIPT -> Status: $($obj.receipt.http_status) ($($obj.receipt.status))" -ForegroundColor $color
            }
        }
        catch { Write-Host $line } 
    }
}
