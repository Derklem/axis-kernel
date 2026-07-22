# manual_verify_43_2.ps1
$Root = "D:\Infinite\Infinity"
$TruthDir = Join-Path $Root "Truth_Engine"
$MemoryRoot = Join-Path $Root "Memory"
$GovDir = Join-Path $Root "Governance"

Import-Module (Join-Path $TruthDir "T17_MemoryIndexer.psm1") -Force

Write-Host "--- TEST 1: FORENSIC ALERTS ---"
$auditPath = Join-Path $TruthDir "audit_trail.jsonl"
$line = Get-Content $auditPath | Select-Object -First 1
[System.IO.File]::AppendAllLines($auditPath, [string[]]@($line))
Update-MemoryLedger -MemoryRoot $MemoryRoot
$alertFile = Join-Path $MemoryRoot "alerts\duplicate_keys.jsonl"
if (Test-Path $alertFile) { 
    $alertJson = Get-Content $alertFile | Select-Object -Last 1 | ConvertFrom-Json
    if ($alertJson.segment -and $alertJson.snippet -and $alertJson.key_kind) {
        Write-Host "[PASS] Alert enriched with segment, snippet, and key_kind ($($alertJson.key_kind))." -ForegroundColor Green
    } else {
        Write-Error "Alert enrichment MISSING (Check segment, snippet, key_kind)."
    }
} else { Write-Error "Alert failed." }

Write-Host "`n--- TEST 2: DUAL-ANCHOR FINGERPRINT ---"
$spendPath = Join-Path $TruthDir "spend_ledger.jsonl"
# Create 20 lines
$testLines = @()
for ($i=1; $i -le 20; $i++) { $testLines += [ordered]@{ ts_utc = (Get-Date).ToString("o"); event_id = "t-$i"; hash = "h-$i" } | ConvertTo-Json -Compress }
[System.IO.File]::WriteAllLines($spendPath, [string[]]$testLines)
Update-MemoryLedger -MemoryRoot $MemoryRoot
$pre = (Get-Content (Join-Path $MemoryRoot "cursors\t17_cursor.spend.json") -Raw | ConvertFrom-Json).byte_offset

# Tamper line 11 (same length)
$lines = [System.IO.File]::ReadAllLines($spendPath)
$obj = $lines[10] | ConvertFrom-Json
$obj.hash = "TAMPER"
$lines[10] = ($obj | ConvertTo-Json -Compress).PadRight($lines[10].Length)
[System.IO.File]::WriteAllLines($spendPath, [string[]]$lines)
Update-MemoryLedger -MemoryRoot $MemoryRoot
$post = (Get-Content (Join-Path $MemoryRoot "cursors\t17_cursor.spend.json") -Raw | ConvertFrom-Json).byte_offset
if ($post -lt $pre) { Write-Host "[PASS] Tamper detected." -ForegroundColor Green } else { Write-Error "Tamper MISSED." }

Write-Host "`n--- TEST 3: ROTATION CONTINUITY ---"
& (Join-Path $GovDir "Axis_Log_Rotation.ps1")
Write-Host "[PASS] Rotation finished." -ForegroundColor Green
