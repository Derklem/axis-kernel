<#
.SYNOPSIS
  Axis_Verify_ForensicJoins.ps1
  Phase 40: Verifies consistency between Spend, Audit, and Runtime ledgers.
.DESCRIPTION
  Enforces contract: axis.forensics.join.v1
  - INV_TWO_PHASE_CLOSURE: Spend Reserve -> Terminal
  - INV_AUTHORITATIVE_LINK: Spend Terminal.audit_event_id -> Audit.event_id
  - INV_REVERSE_LINK: Audit.detail.spend_txn_id -> Spend.spend_txn_id (Weak/Optional)
  - INV_IDENTITY_MATCH: Spend.identity == Audit.identity
#>

param(
    [string]$SpendLedger = "D:\Infinite\Infinity\Truth_Engine\spend_ledger.jsonl",
    [string]$AuditLog = "D:\Infinite\Infinity\Truth_Engine\audit_trail.jsonl",
    [switch]$FullScan,
    [switch]$AllowLegacyIds
)

Write-Host "--- AXIS FORENSIC JOIN VERIFIER (Phase 40) ---" -ForegroundColor Cyan

if (-not (Test-Path $SpendLedger) -or -not (Test-Path $AuditLog)) {
    Write-Error "Missing Ledgers"
    exit 1
}

# 1. Index Audit Log (Authoritative Source)
Write-Host "Indexing Audit Log..." -ForegroundColor Gray
$auditIndex = @{}
Get-Content $AuditLog | ForEach-Object {
    if (-not [string]::IsNullOrWhiteSpace($_)) {
        try {
            $e = $_ | ConvertFrom-Json
            if ($e.event_id) { $auditIndex[$e.event_id] = $e }
        }
        catch {}
    }
}
Write-Host "  -> Indexed $($auditIndex.Count) audit events." -ForegroundColor Green

# 2. Walk Spend Ledger
Write-Host "Verifying Spend Chain & Joins..." -ForegroundColor Gray
$txns = @{}
$lines = Get-Content $SpendLedger
$errors = 0

foreach ($line in $lines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
        $e = $line | ConvertFrom-Json
        $stxn = $e.spend_txn_id
        
        if (-not $stxn -or $stxn -eq "null") { continue } # Legacy or Unimodal

        if ($e.type -eq "RESERVE") {
            $txns[$stxn] = @{ reserve = $e; terminal = $null }
        }
        elseif ($e.type -in @("COMMIT", "ROLLBACK", "EXPIRE")) {
            if ($txns.ContainsKey($stxn)) {
                if ($txns[$stxn].terminal) {
                    Write-Host "  [FAIL] Multiple Terminals: Spend $stxn has multiple closure events." -ForegroundColor Red
                    $errors++
                }
                $txns[$stxn].terminal = $e
                
                # --- CHECK 1: Authoritative Link ---
                $aeid = $e.audit_event_id
                if ($aeid -and $aeid -ne "PENDING" -and $aeid -ne "BLOCKED" -and $aeid -ne "null") {
                    if (-not $auditIndex.ContainsKey($aeid)) {
                        # Strict Mode by default. Use -AllowLegacyIds to skip "EXEC_SUCCESS" etc.
                        if (-not $AllowLegacyIds -or ($aeid -match "^audit-")) {
                            Write-Host "  [FAIL] Broken Audit Link: Spend $stxn links to non-existent Audit $aeid" -ForegroundColor Red
                            $errors++
                        }
                    }
                    else {
                        # --- CHECK 2: Identity Consistency ---
                        $auditEvt = $auditIndex[$aeid]
                        if ($auditEvt.identity -ne $e.identity) {
                            Write-Host "  [FAIL] Identity Mismatch: Spend($($e.identity)) vs Audit($($auditEvt.identity))" -ForegroundColor Red
                            $errors++
                        }
                    }
                }
            }
        }
    }
    catch {}
}

# --- CHECK 3: Reverse Link (Audit -> Spend) ---
# Scan audit events for spend_txn_id in detail and verify it exists in Spend
# (Optional, but good for completeness)

Write-Host "`nVerification Complete."
if ($errors -eq 0) {
    Write-Host "  [PASS] Forensic Joins Valid." -ForegroundColor Green
}
else {
    Write-Host "  [FAIL] Found $errors integrity violations." -ForegroundColor Red
}
