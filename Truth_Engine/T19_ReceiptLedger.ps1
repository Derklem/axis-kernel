<#
.SYNOPSIS
  T19_ReceiptLedger.ps1
  Auditable Transaction Ledger for External Writes.
.DESCRIPTION
  - WRITE_ATTEMPT: Log intent to write.
  - WRITE_RECEIPT: Log result of write.
  - INDEX: (Function only) Rebuild index.
#>
param(
    [ValidateSet("WRITE_ATTEMPT", "WRITE_RECEIPT", "INDEX", "REPORT", "GET_STATUS")]
    [string]$Action = "REPORT",
    
    [string]$RunId,
    [string]$CorrId,
    [string]$OpType, # POST, REGISTER
    [string]$Target, # moltbook:general
    [object]$AttemptData,
    [object]$ReceiptData
)

$FSLib = "D:\Infinite\Axis_FS_Lib.ps1"
if (Test-Path $FSLib) { . $FSLib }

# --- CONFIG ---
$ReceiptsDir = "D:\Infinite\Infinity\Runtime\Receipts"
$LedgerFile = Join-Path $ReceiptsDir "Receipt_Ledger.jsonl"

if (-not (Test-Path $ReceiptsDir)) { New-Item -ItemType Directory -Path $ReceiptsDir -Force | Out-Null }

function Append-Ledger($obj) {
    if (Get-Command Append-JsonlLineNoBom -ErrorAction SilentlyContinue) {
        Append-JsonlLineNoBom -Path $LedgerFile -Data $obj
    }
    else {
        $obj | ConvertTo-Json -Compress | Add-Content -Path $LedgerFile -Encoding UTF8
    }
}

if ($Action -eq "WRITE_ATTEMPT") {
    if (-not $RunId -or -not $CorrId) { Write-Error "RunId/CorrId required"; return }
    
    $entry = [ordered]@{
        ts      = (Get-Date).ToUniversalTime().ToString("o")
        run_id  = $RunId
        corr_id = $CorrId
        type    = "ATTEMPT"
        action  = $OpType
        target  = $Target
        attempt = $AttemptData
    }
    
    Invoke-WithMutex -Name "Global\Axis_ReceiptLedger_Mutex" -TimeoutMs 2000 -ScriptBlock {
        Append-Ledger $entry
    }
    Write-Host "Logged Attempt: $CorrId" -ForegroundColor Cyan
}

if ($Action -eq "WRITE_RECEIPT") {
    if (-not $RunId -or -not $CorrId) { Write-Error "RunId/CorrId required"; return }
    
    $entry = [ordered]@{
        ts      = (Get-Date).ToUniversalTime().ToString("o")
        run_id  = $RunId
        corr_id = $CorrId
        type    = "RECEIPT"
        action  = $OpType
        target  = $Target
        receipt = $ReceiptData
        reality = @{
            class  = "L0_OBSERVED"
            source = if ($ReceiptData.method) { $ReceiptData.method } else { "client_response" }
        }
    }
    
    Invoke-WithMutex -Name "Global\Axis_ReceiptLedger_Mutex" -TimeoutMs 2000 -ScriptBlock {
        Append-Ledger $entry
    }
    Write-Host "Logged Receipt: $CorrId ($($ReceiptData.status))" -ForegroundColor Green
}

if ($Action -eq "GET_STATUS") {
    if (-not $CorrId) { Write-Error "CorrId required"; return }
    if (-not (Test-Path $LedgerFile)) { return $null }
    
    # Return latest status for this CorrId
    $last = $null
    foreach ($line in (Get-Content $LedgerFile -Tail 1000 -Encoding UTF8)) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $evt = $line | ConvertFrom-Json
            if ($evt.corr_id -eq $CorrId) { $last = $evt }
        }
        catch { continue }
    }
    return $last
}

if ($Action -eq "REPORT") {
    if (Test-Path $LedgerFile) {
        $recs = Get-Content $LedgerFile -Tail 10 | ConvertFrom-Json
        $recs | Select-Object ts, type, action, corr_id, @{n = "Result"; e = { $_.receipt.status } } | Format-Table -AutoSize
    }
    else {
        Write-Host "No Ledger Found."
    }
}
