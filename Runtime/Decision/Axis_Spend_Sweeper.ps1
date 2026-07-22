# Axis_Spend_Sweeper.ps1
# Scans the Spend Ledger for dangling RESERVE transactions and expires them.
# Usage: Run on system startup or periodic maintenance.

param(
    [string]$SpendLedger = "D:\Infinite\Infinity\Truth_Engine\spend_ledger.jsonl",
    [switch]$DryRun
)

$SpendModule = "D:\Infinite\Infinity\Truth_Engine\Axis_Spend_Manager.psm1"
if (-not (Test-Path $SpendModule)) { Write-Error "Spend Module not found."; exit 1 }
Import-Module $SpendModule -Force

if (-not (Test-Path $SpendLedger)) { Write-Host "No ledger found." -ForegroundColor Yellow; exit 0 }

Write-Host "--- AXIS SPEND SWEEPER ---" -ForegroundColor Cyan

$lines = Get-Content $SpendLedger
$txnMap = @{}

# 1. Build State
foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
        $e = $line | ConvertFrom-Json
        if ($null -ne $e.spend_txn_id -and -not [string]::IsNullOrWhiteSpace($e.spend_txn_id)) {
            if ($e.type -eq "RESERVE") {
                if (-not $txnMap.ContainsKey($e.spend_txn_id)) {
                    $txnMap[$e.spend_txn_id] = @{ state = "OPEN"; reserve_line = $e }
                }
            }
            elseif ($e.type -in @("COMMIT", "ROLLBACK", "EXPIRE")) {
                if ($txnMap.ContainsKey($e.spend_txn_id)) {
                    $txnMap[$e.spend_txn_id].state = "CLOSED"
                }
            }
        }
    }
    catch {}
}

# 2. Identify and Expire
$expiredCount = 0
foreach ($txnId in $txnMap.Keys) {
    $info = $txnMap[$txnId]
    if ($info.state -eq "OPEN") {
        $r = $info.reserve_line
        Write-Host "  [OPEN] found: $txnId (Reserved: $($r.ts_utc))" -ForegroundColor Yellow
        
        if (-not $DryRun) {
            # Append EXPIRE
            Write-Host "    -> Expiring..." -NoNewline
            $hash = Append-AxisSpendEntry `
                -IntentId $r.intent_id `
                -CorrId $r.corr_id `
                -Identity $r.identity `
                -AuditEventId "EXPIRED_BY_SWEEPER" `
                -OpKey $r.op_key `
                -SpendTxnId $txnId `
                -Type "EXPIRE" `
                -Units 0 # Release?
            Write-Host " DONE ($hash)" -ForegroundColor Green
            $expiredCount++
        }
    }
}

if ($expiredCount -eq 0) {
    Write-Host "System Clean. No dangling transactions found." -ForegroundColor Green
}
else {
    Write-Host "Sweeper Run Complete. Expired $expiredCount transactions." -ForegroundColor Cyan
}
