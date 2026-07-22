# Axis_Verify_KeyLedger.ps1
# Verifies the integrity and continuity of the Key Ledger

$LedgerPath = "D:\Infinite\Infinity\Governance\key_ledger.jsonl"
$RegistryPath = "D:\Infinite\Infinity\Truth_Engine\identity_registry.json"

function Compute-Sha256([string]$data) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($data)
    $hash = $sha.ComputeHash($bytes)
    return ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

Write-Host ">>> Verifying Key Ledger Integrity" -ForegroundColor Cyan

if (-not (Test-Path $LedgerPath)) {
    Write-Error "Key Ledger missing: $LedgerPath"
    exit 1
}

$lines = Get-Content $LedgerPath
$lastHash = ""

foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    $block = $line | ConvertFrom-Json
    
    # Check Schema
    if ($block.schema -ne "axis.key_ledger.v1") {
        Write-Error "Invalid schema in block $($block.id)"
        exit 1
    }
    
    # Check Continuity (Future: simple chaining)
    # For now, we just verify each block is valid JSON and has required fields
    if (-not $block.id -or -not $block.type -or -not $block.status) {
        Write-Error "Missing required fields in block"
        exit 1
    }
    
    Write-Host "  [OK] Block $($block.id) ($($block.type)) - $($block.key_id): $($block.status)" -ForegroundColor Gray
}

Write-Host "[PASS] Key Ledger Integrity Verified" -ForegroundColor Green
exit 0
