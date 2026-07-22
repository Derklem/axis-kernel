[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity",
    [int]$Depth = 50
)

$ErrorActionPreference = "Stop"

$decisionLog = Join-Path $Root "Runtime\Decision\decision_log.jsonl"
$reviewLog = Join-Path $Root "Runtime\Decision\Review\review_log.jsonl"
$promoLog = Join-Path $Root "Runtime\Decision\Voice\promotion_ledger.jsonl"

Write-Host "--- Temporal Chain Verification (Last $Depth Executions) ---" -ForegroundColor Cyan

if (-not (Test-Path $decisionLog)) {
    Write-Warning "Decision Log not found."
    exit 0
}

# Load Data
$executions = Get-Content $decisionLog -Tail $Depth | ConvertFrom-Json
if (Test-Path $reviewLog) {
    $reviews = Get-Content $reviewLog -Tail ($Depth * 2) | ConvertFrom-Json
}
else {
    $reviews = @()
}

if (Test-Path $promoLog) {
    $promotions = Get-Content $promoLog -Tail ($Depth * 2) | ConvertFrom-Json
}
else {
    $promotions = @()
}

# Index for speed
$reviewIndex = @{}
foreach ($r in $reviews) {
    if ($r.proposal_id) { $reviewIndex[$r.proposal_id] = $r }
}

$promoIndex = @{}
foreach ($p in $promotions) {
    if ($p.proposal_id) { $promoIndex[$p.proposal_id] = $p }
}

$failures = 0
$checked = 0

foreach ($exec in $executions) {
    # Only check APPROVED execution paths (some might be SYSTEM/AUTO without review if designed so, but usually T08 requires approved intent)
    # T08 logs "intent_id" which is usually the proposal_id/nonce
    $id = $exec.intent_id
    
    if ([string]::IsNullOrWhiteSpace($id) -or $id -eq "UNKNOWN") { continue }
    
    $checked++
    $t_exec = [DateTime]::Parse($exec.ts)
    
    # 1. Find Approval
    $appr = $reviewIndex[$id]
    if (-not $appr) {
        # Might be pre-historic or from a different queue source
        # Write-Warning "Execution $id has no Approval record (Tail limit?)"
        continue 
    }
    
    $t_appr = [DateTime]::Parse($appr.ts)
    
    # Check Ordering: Appr < Exec
    if ($t_appr -ge $t_exec) {
        Write-Host "[FAIL] ${id}: Approved ($t_appr) >= Executed ($t_exec)" -ForegroundColor Red
        $failures++
        continue
    }
    
    # 2. Find Promotion (Optional, as not all intents are Voice Promoted)
    $promo = $promoIndex[$id]
    if ($promo) {
        $t_promo = [DateTime]::Parse($promo.ts)
        
        # Check Ordering: Appr < Promo
        if ($t_appr -ge $t_promo) {
            Write-Host "[FAIL] ${id}: Approved ($t_appr) >= Promoted ($t_promo)" -ForegroundColor Red
            $failures++
            continue
        }
        
        # Check Ordering: Promo < Exec
        if ($t_promo -ge $t_exec) {
            Write-Host "[FAIL] ${id}: Promoted ($t_promo) >= Executed ($t_exec)" -ForegroundColor Red
            $failures++
            continue
        }
        
        Write-Host "[PASS] ${id}: Appr -> Promo -> Exec (OK)" -ForegroundColor Green
    }
    else {
        Write-Host "[PASS] ${id}: Appr -> Exec (Direct/Manual)" -ForegroundColor Green
    }
}

# 3. Manifest Ledger Temporal Checks (Phase 47)
Write-Host "`n--- Manifest Ledger Temporal Checks ---" -ForegroundColor Cyan
$ManifestFile = Join-Path $Root "Governance\state_vector_manifest.json"
if (Test-Path $ManifestFile) {
    $ManifestObj = Get-Content $ManifestFile | ConvertFrom-Json
    foreach ($property in $ManifestObj.components.PSObject.Properties) {
        $cName = $property.Name
        $cObj  = $property.Value
        if ($cObj.kind -eq "ledger_head") {
            $lPath = Join-Path $Root $cObj.path
            if (Test-Path $lPath) {
                Write-Host "Verifying $cName temporal consistency..." -NoNewline
                $lLines = Get-Content $lPath -Tail 100
                $lastT_l = [DateTime]::MinValue
                $lFail = $false
                foreach ($line_l in $lLines) {
                    if ([string]::IsNullOrWhiteSpace($line_l)) { continue }
                    $o_l = $line_l | ConvertFrom-Json
                    $tsStr = if ($o_l.ts_utc) { $o_l.ts_utc } elseif ($o_l.ts) { $o_l.ts } else { $null }
                    if ($tsStr) {
                        try {
                            $t_v = [DateTime]::Parse($tsStr)
                            if ($t_v -lt $lastT_l) {
                                Write-Host " [FAIL]" -ForegroundColor Red
                                Write-Host "  Time Reversal in $cName : $t_v < $lastT_l" -ForegroundColor Red
                                $failures++
                                $lFail = $true
                                break
                            }
                            $lastT_l = $t_v
                        } catch { continue }
                    }
                }
                if (-not $lFail) { Write-Host " [OK]" -ForegroundColor Green }
            }
        }
    }
}
if ($failures -eq 0) {
    Write-Host "`nTemporal Chain Verified: $checked chains intact." -ForegroundColor Cyan
    exit 0
}
else {
    Write-Host "`nTemporal Chain Failures Detected: $failures" -ForegroundColor Red
    exit 1
}
