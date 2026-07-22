# Phase7_KillVerifier.ps1
param(
    [string]$ExpectedCount = 0
)

$EffectsFile = "D:\Infinite\Infinity\Runtime\Decision\Tests\killtest_effects.jsonl"
$ReceiptFile = "D:\Infinite\Infinity\Truth_Engine\receipt_ledger.jsonl"
$ApprovedFile = "D:\Infinite\Infinity\Runtime\Decision\approved_intents.jsonl"

Write-Host "--- KILL TEST VERIFICATION ---" -ForegroundColor Cyan

$Failures = @()

# 1. Check for Duplicate Side Effects
if (Test-Path $EffectsFile) {
    $effects = Get-Content $EffectsFile | ForEach-Object { try { $_ | ConvertFrom-Json } catch {} }
    $starts = $effects | Where-Object { $_.marker -eq "START" }
    $dones = $effects | Where-Object { $_.marker -eq "DONE" }
    
    $startGroups = $starts | Group-Object corr_id
    foreach ($grp in $startGroups) {
        if ($grp.Count -gt 1) {
            $Failures += "DUPLICATE_START: Correlation $($grp.Name) started $($grp.Count) times!"
        }
    }
    
    $doneGroups = $dones | Group-Object corr_id
    foreach ($grp in $doneGroups) {
        if ($grp.Count -gt 1) {
            $Failures += "DUPLICATE_DONE: Correlation $($grp.Name) finished $($grp.Count) times!"
        }
    }
    
    Write-Host "Side Effects: $($starts.Count) Starts, $($dones.Count) Dones." -ForegroundColor Gray
}

# 2. Check for Duplicate Receipts
if (Test-Path $ReceiptFile) {
    $receipts = Get-Content $ReceiptFile | ForEach-Object { try { $_ | ConvertFrom-Json } catch {} }
    $receiptGroups = $receipts | Where-Object { $_.type -eq "RECEIPT" } | Group-Object corr_id
    foreach ($grp in $receiptGroups) {
        if ($grp.Count -gt 1) {
            $Failures += "DUPLICATE_RECEIPT: Correlation $($grp.Name) has $($grp.Count) receipts!"
        }
    }
    Write-Host "Receipts Ledger: $($receipts.Count) entries total." -ForegroundColor Gray
}

# 3. Check for Corruption
function Test-JsonlParseable($path) {
    if (-not (Test-Path $path)) { return $true }
    try {
        Get-Content $path | ForEach-Object { $_ | ConvertFrom-Json | Out-Null }
        return $true
    }
    catch {
        return $false
    }
}

if (-not (Test-JsonlParseable $ApprovedFile)) { $Failures += "CORRUPTED_QUEUE: $ApprovedFile" }
if (-not (Test-JsonlParseable $ReceiptFile)) { $Failures += "CORRUPTED_LEDGER: $ReceiptFile" }

# 4. Summary
if ($Failures.Count -eq 0) {
    Write-Host "VERIFICATION PASSED: No invariant violations detected." -ForegroundColor Green
}
else {
    Write-Host "VERIFICATION FAILED!" -ForegroundColor Red
    $Failures | ForEach-Object { Write-Host "  [!] $_" -ForegroundColor Yellow }
}

return $Failures
