# Fix-AuditChain.ps1
# Utility to repair audit trail integrity by re-computing hash chains.
# WARNING: This mutates the audit log. Use only for recovery.

param(
    [string]$AuditLogFile = "D:\Infinite\Infinity\Truth_Engine\audit_trail.jsonl",
    [switch]$Repair
)

if (-not (Test-Path $AuditLogFile)) {
    Write-Host "[ERROR] Log not found: $AuditLogFile" -ForegroundColor Red
    exit 1
}

# Re-compute hash
if (-not (Get-Module T08_AuditLogger)) {
    Import-Module "D:\Infinite\Infinity\Truth_Engine\T08_AuditLogger.psm1" -Force
}

$lines = Get-Content $AuditLogFile
$newLines = @()
$lastHash = $null
$lineNum = 0
$changes = 0

Write-Host "Analyzing $AuditLogFile..." -ForegroundColor Gray

foreach ($line in $lines) {
    $lineNum++
    if ([string]::IsNullOrWhiteSpace($line)) { continue }

    try {
        $event = $line | ConvertFrom-Json
        
        # Check prev_hash
        if ($lineNum -gt 1 -and $event.prev_hash -ne $lastHash) {
            Write-Host "  [FIX] Line ${lineNum}: Correcting prev_hash ($($event.prev_hash) -> $lastHash)" -ForegroundColor Yellow
            $event.prev_hash = $lastHash
            $changes++
        }

        # Build hashtable for module function (Handles PSCustomObject conversion)
        $h_hashes = @{}
        if ($event.hashes) {
            foreach ($p in $event.hashes.PSObject.Properties) {
                $h_hashes[$p.Name] = $p.Value
            }
        }

        $h_detail = @{}
        if ($event.detail) {
            foreach ($p in $event.detail.PSObject.Properties) {
                $h_detail[$p.Name] = $p.Value
            }
        }
        
        $h = @{}
        foreach ($p in $event.PSObject.Properties) {
            if ($p.Name -eq "hashes") { $h["hashes"] = $h_hashes }
            elseif ($p.Name -eq "detail") { $h["detail"] = $h_detail }
            elseif ($p.Name -ne "hash") { $h[$p.Name] = $p.Value }
        }
        
        $core = Build-AuditEventJson $h
        $newHash = Hash-Sha256Hex $core
        
        if ($event.hash -ne $newHash) {
            Write-Host "  [FIX] Line ${lineNum}: Correcting hash ($($event.hash) -> $newHash)" -ForegroundColor Yellow
            $changes++
        }
        
        $finalLine = $core.Substring(0, $core.Length - 1) + ',"hash":"' + $newHash + '"}'
        $newLines += $finalLine
        $lastHash = $newHash
    }
    catch {
        Write-Host "  [ERROR] Line ${lineNum}: Error processing line. $_" -ForegroundColor Red
        exit 1
    }
}

if ($changes -eq 0) {
    Write-Host "[PASS] No repairs needed." -ForegroundColor Green
}
else {
    Write-Host "[WARN] $changes repairs identified." -ForegroundColor Yellow
    if ($Repair) {
        # 1. Archive Original
        $ArchiveDir = "D:\Infinite\Infinity\Truth_Engine\Archive"
        if (-not (Test-Path $ArchiveDir)) { New-Item $ArchiveDir -ItemType Directory -Force | Out-Null }
        $ts = (Get-Date).ToUniversalTime().ToString("yyyyMMdd_HHmmss")
        $archivePath = Join-Path $ArchiveDir ("audit_trail_{0}_corrupted.jsonl" -f $ts)
        Copy-Item $AuditLogFile $archivePath -Force

        $inputHead = "UNKNOWN"
        try { $inputHead = (Get-Content $archivePath -Tail 1 | ConvertFrom-Json).hash } catch { }

        # 2. Apply Repair
        $newLines | Set-Content $AuditLogFile -Encoding utf8
        Write-Host "[SUCCESS] Log repaired and over-written. Original archived to $archivePath" -ForegroundColor Green

        # 3. Meta-Audit (Repair Ledger)
        $RepairLedger = "D:\Infinite\Infinity\Truth_Engine\audit_repair_ledger.jsonl"
        $AnchorFile = "D:\Infinite\Infinity\Truth_Engine\anchors.jsonl"
        $toolHash = (Get-FileHash "D:\Infinite\Infinity\Governance\Fix-AuditChain.ps1" -Algorithm SHA256).Hash.ToLower()
        
        $anchorState = "UNKNOWN"
        if (Test-Path $AnchorFile) {
            try { $anchorState = (Get-Content $AnchorFile -Tail 1 | ConvertFrom-Json).hash } catch {}
        }

        $prevRepairHash = $null
        if (Test-Path $RepairLedger) {
            try { $prevRepairHash = (Get-Content $RepairLedger -Tail 1 | ConvertFrom-Json).hash } catch {}
        }

        $repairEntry = [ordered]@{
            schema            = "axis.audit.repair.v1"
            repair_event_id   = "repair-" + [Guid]::NewGuid().ToString().Substring(0, 8)
            ts_utc            = (Get-Date).ToUniversalTime().ToString("o")
            operator_identity = "system:admin"
            input_head_hash   = $inputHead
            output_head_hash  = $lastHash
            range_rewritten   = "1-$lineNum"
            reason            = "Automated recovery of hash chain integrity"
            tool_hash         = "sha256:$toolHash"
            anchor_at_repair  = $anchorState
            prev_hash         = $prevRepairHash
        }
        
        $json = $repairEntry | ConvertTo-Json -Compress
        $h = Hash-Sha256Hex $json
        $final = $json.Substring(0, $json.Length - 1) + ',"hash":"' + $h + '"}'
        $final | Add-Content $RepairLedger -Encoding utf8
        Write-Host "[INFO] Forensic trace recorded in audit_repair_ledger.jsonl" -ForegroundColor Cyan
    }
    else {
        Write-Host "[INFO] Dry run. Use -Repair to apply changes." -ForegroundColor Cyan
    }
}
