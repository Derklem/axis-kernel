# Axis_Verify_AuditTrail.ps1
# Verifies the integrity and continuity of the Axis Audit Trail.

param(
    [string]$AuditLogFile = "D:\Infinite\Infinity\Truth_Engine\audit_trail.jsonl"
)

Write-Host "--- Axis Audit Trail Verifier (Phase 38) ---" -ForegroundColor Cyan

if (-not (Test-Path $AuditLogFile)) {
    Write-Host "[FAIL] Audit Log missing: $AuditLogFile" -ForegroundColor Red
    exit 1
}

# Import Deterministic Builder & Hasher
if (-not (Get-Module T08_AuditLogger)) {
    $AuditModule = "D:\Infinite\Infinity\Truth_Engine\T08_AuditLogger.psm1"
    if (Test-Path $AuditModule) { Import-Module $AuditModule -Force }
}

Write-Host "Verifying $AuditLogFile..." -ForegroundColor Gray

$lines = Get-Content $AuditLogFile
$lastHash = $null
$lineNum = 0
$errors = 0

foreach ($line in $lines) {
    $lineNum++
    if ([string]::IsNullOrWhiteSpace($line)) { continue }

    try {
        # 1. Strict JSON Parse
        $event = $null
        try {
            $event = $line | ConvertFrom-Json -ErrorAction Stop
        }
        catch {
            Write-Host "  [FAIL] Line ${lineNum}: Mismatched or partial JSON. Parse failed." -ForegroundColor Red
            $errors++
            continue
        }

        # 2. Verify Property Presence (Normalized Schema v2)
        $required = @("schema", "ts_utc", "event_id", "result", "result_code", "detail", "prev_hash", "hash", "hashes")
        foreach ($r in $required) {
            if ($null -eq ($event.PSObject.Properties | Where-Object { $_.Name -eq $r })) {
                Write-Host "  [FAIL] Line ${lineNum}: Missing property '$r'" -ForegroundColor Red
                $errors++
            }
        }

        if ($event.schema -ne "axis.audit.event.v2") {
            Write-Host "  [FAIL] Line ${lineNum}: Invalid schema '$($event.schema)'. Expected axis.audit.event.v2" -ForegroundColor Red
            $errors++
        }

        # 3. Verify Hash Chain
        if ($lineNum -eq 1) {
            if ($null -ne $event.prev_hash) {
                Write-Host "  [FAIL] Line ${lineNum}: Genesis prev_hash is not null" -ForegroundColor Red
                $errors++
            }
            $lastTs = [DateTime]::Parse($event.ts_utc)
        }
        else {
            if ($event.prev_hash -ne $lastHash) {
                Write-Host "  [FAIL] Line ${lineNum}: Chain break. Expected $lastHash, got $($event.prev_hash)" -ForegroundColor Red
                $errors++
            }
            
            # 3b. INV_TEMPORAL_LINK (Monotonicity: UTC, ISO8601, Equality allowed)
            $currentTs = [DateTime]::Parse($event.ts_utc)
            if ($currentTs -lt $lastTs) {
                Write-Host "  [FAIL] Line ${lineNum}: Temporal violation. Ts $currentTs is earlier than last $lastTs" -ForegroundColor Red
                $errors++
            }
            $lastTs = $currentTs
        }

        # 4. Content Hash Verification (Reconstruct & Recompute)
        if (Get-Command Build-AuditEventJson -ErrorAction SilentlyContinue) {
            # Convert PSCustomObject to Hashtables for Builder
            $h_hashes = @{}
            if ($event.hashes) {
                foreach ($p in $event.hashes.PSObject.Properties) { $h_hashes[$p.Name] = $p.Value }
            }
            $h_detail = @{}
            if ($event.detail) {
                foreach ($p in $event.detail.PSObject.Properties) { $h_detail[$p.Name] = $p.Value }
            }
            
            $h = @{}
            foreach ($p in $event.PSObject.Properties) {
                if ($p.Name -eq "hashes") { $h["hashes"] = $h_hashes }
                elseif ($p.Name -eq "detail") { $h["detail"] = $h_detail }
                elseif ($p.Name -ne "hash") { $h[$p.Name] = $p.Value }
            }

            $core = Build-AuditEventJson $h
            $computed = Hash-Sha256Hex $core
            
            if ($computed -ne $event.hash) {
                Write-Host "  [FAIL] Line ${lineNum}: Content hash mismatch. Computed $computed, Logged $($event.hash)" -ForegroundColor Red
                $errors++
            }
        }

        $lastHash = $event.hash
    }
    catch {
        Write-Host "  [FAIL] Line ${lineNum}: Unexpected error: $_" -ForegroundColor Red
        $errors++
    }
}

if ($errors -eq 0) {
    Write-Host "[PASS] Audit Trail Integrity Verified ($lineNum entries)" -ForegroundColor Green
    if ($lastHash) { Write-Host "Head Hash: $lastHash" }
    exit 0
}
else {
    Write-Host "[FAIL] Audit Trail Integrity Corruption Detected ($errors errors)" -ForegroundColor Red
    exit 1
}
