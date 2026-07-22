# Axis_Verify_EconomicForensics.ps1
# Verifies the integrity of the Economic Forensics Spend Ledger.

param(
    [string]$SpendLedger = "D:\Infinite\Infinity\Truth_Engine\spend_ledger.jsonl",
    [string]$AuditLog = "D:\Infinite\Infinity\Truth_Engine\audit_trail.jsonl",
    [switch]$AllowOrphanTerminals
)

Write-Host "--- AXIS ECONOMIC FORENSICS VERIFIER ---" -ForegroundColor Cyan

if (-not (Test-Path $SpendLedger)) {
    Write-Host "[FAIL] Spend Ledger not found: $SpendLedger" -ForegroundColor Red
    exit 1
}

# 1. Load Spend Module for Hashing
$SpendModule = "D:\Infinite\Infinity\Truth_Engine\Axis_Spend_Manager.psm1"
if (Test-Path $SpendModule) { Import-Module $SpendModule -Force }

$lines = Get-Content $SpendLedger
$lastHash = $null
$errors = 0
$lineNum = 0

foreach ($line in $lines) {
    $lineNum++
    if ([string]::IsNullOrWhiteSpace($line)) { continue }

    try {
        $event = $line | ConvertFrom-Json
        
        # 1. Verify Hash Chain
        if ($lineNum -gt 1 -and $event.prev_hash -ne $lastHash) {
            Write-Host "  [FAIL] Line ${lineNum}: Hash chain break! Prev: $($event.prev_hash) | Expected: $lastHash" -ForegroundColor Red
            $errors++
        }

        # 2. Verify Schema
        if ($event.schema -ne "axis.spend.event.v1") {
            Write-Host "  [FAIL] Line ${lineNum}: Invalid schema '$($event.schema)'" -ForegroundColor Red
            $errors++
        }

        # 3. Verify Self-Hash
        # We need Build-SpendEventJson from module
        if (Get-Command Build-SpendEventJson -ErrorAction SilentlyContinue) {
            # Build hashable core (excluding trailing hash)
            # Simpler: Use the hashing utility if available
            $h_hashtable = @{}
            foreach ($p in $event.PSObject.Properties) {
                if ($p.Name -ne "hash") { $h_hashtable[$p.Name] = $p.Value }
            }
            $core = Build-SpendEventJson $h_hashtable
            $computed = Hash-Sha256Hex $core
            if ($event.hash -ne $computed) {
                Write-Host "  [FAIL] Line ${lineNum}: Content hash mismatch! $($event.hash) != $computed" -ForegroundColor Red
                $errors++
            }
        }

        $lastHash = $event.hash
    }
    catch {
        Write-Host "  [ERROR] Line ${lineNum}: Failed to parse JSON. $_" -ForegroundColor Red
        $errors++
    }
}

# 2. Verify Audit Join (Sampling)
Write-Host "Verifying Audit-Spend Join..." -ForegroundColor Gray
if (Test-Path $AuditLog) {
    # Check last few COMMIT events have audit-event-id present in audit log
    $commitEvents = $lines | ForEach-Object { try { $_ | ConvertFrom-Json } catch { $null } } | Where-Object { $_.type -eq "COMMIT" } | Select-Object -Last 5
    if ($commitEvents) {
        $auditContent = Get-Content $AuditLog -Raw
        foreach ($ce in $commitEvents) {
            if ($auditContent -notmatch $ce.audit_event_id) {
                Write-Host "  [WARN] Spend event $($ce.event_id) references unknown audit_event_id: $($ce.audit_event_id)" -ForegroundColor Yellow
            }
        }
    }
}


# 3. Two-Phase Spend Invariant (Completion)
Write-Host "Verifying Spend Invariants (Reserve -> Commit/Rollback/Expire)..." -ForegroundColor Gray
$txnMap = @{}
foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
        $e = $line | ConvertFrom-Json
        if ($null -ne $e.spend_txn_id -and -not [string]::IsNullOrWhiteSpace($e.spend_txn_id)) {
            if ($e.type -eq "RESERVE") {
                if (-not $txnMap.ContainsKey($e.spend_txn_id)) {
                    $txnMap[$e.spend_txn_id] = @{ state = "OPEN"; reserve_line = $e; updates = 0 }
                }
            }
            elseif ($e.type -in @("COMMIT", "ROLLBACK", "EXPIRE")) {
                if ($txnMap.ContainsKey($e.spend_txn_id)) {
                    $txnMap[$e.spend_txn_id].state = "CLOSED"
                    $txnMap[$e.spend_txn_id].updates++
                }
                else {
                    # Terminal without Reserve
                    if (-not $AllowOrphanTerminals) {
                        Write-Host "  [FAIL] Orphaned Terminal Event ($($e.type)) for Txn $($e.spend_txn_id) at $($e.ts_utc)" -ForegroundColor Red
                        $errors++
                    }
                    else {
                        Write-Host "  [WARN] Orphaned Terminal Event ($($e.type)) for Txn $($e.spend_txn_id) (Allowed)" -ForegroundColor Yellow
                    }
                }
            }
        }
    }
    catch {}
}

# Check for Open Txns & Multiple Terminals
$openCount = 0
foreach ($txnId in $txnMap.Keys) {
    $info = $txnMap[$txnId]
    
    # 1. Open Check
    if ($info.state -eq "OPEN") {
        Write-Host "  [FAIL] Dangling Spend Transaction: $txnId (Reserved at $($info.reserve_line.ts_utc))" -ForegroundColor Red
        $openCount++
        $errors++
    }
    
    # 2. Duplicate Terminal Check
    if ($info.updates -gt 1) {
        Write-Host "  [FAIL] Multiple Terminal Events for Txn $txnId (Count: $($info.updates))" -ForegroundColor Red
        $errors++
    }
}
if ($openCount -eq 0) {
    Write-Host "  [PASS] All ($($txnMap.Count)) spend transactions are terminalized." -ForegroundColor Green
}


if ($errors -eq 0) {
    Write-Host "[PASS] Economic Forensics Integrity Verified ($lineNum events)." -ForegroundColor Green
    exit 0
}
else {
    Write-Host "[FAIL] Economic Forensics Integrity FAILED ($errors errors)." -ForegroundColor Red
    exit 1
}
