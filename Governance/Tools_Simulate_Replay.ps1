param(
    [string]$Root = "D:\Infinite\Infinity"
)

$LedgerFile = Join-Path $Root "Governance\policy_update_ledger.jsonl"
$lines = Get-Content $LedgerFile
$last = $lines | Select-Object -Last 1
[System.IO.File]::AppendAllText($LedgerFile, $last + "`n", [System.Text.Encoding]::UTF8)
Write-Host "Replay Injection Complete."
