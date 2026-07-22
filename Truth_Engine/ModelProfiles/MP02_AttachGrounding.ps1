<# 
.SYNOPSIS
    MP02 Attach Grounding
.DESCRIPTION
    Scans pending model claims and attaches Truth Engine grounding results.
#>

param(
    [string]$RootPath = "D:\Infinite\Infinity\Truth_Engine",
    [string]$LogPath = "D:\Infinite\Infinity\Truth_Engine\ModelProfiles\TE_Model_Claim_Log.jsonl",
    [string]$EnrichedPath = "D:\Infinite\Infinity\Truth_Engine\ModelProfiles\TE_Model_Claim_Grounded.jsonl"
)

$triadConsult = Join-Path $RootPath "Triad_Consult.ps1"

if (-not (Test-Path $LogPath)) {
    Write-Host "[MP02] No model claims to ground." -ForegroundColor Gray
    return
}

# 1. Load Pending Claims
$allClaims = @(Get-Content $LogPath | ForEach-Object { $_ | ConvertFrom-Json })
$pending = $allClaims | Where-Object { $_.status -eq "PENDING_GROUNDING" }

if ($pending.Count -eq 0) {
    Write-Host "[MP02] No pending claims." -ForegroundColor Gray
    return
}

$enrichedCount = 0

foreach ($claim in $pending) {
    Write-Host "[MP02] Grounding: $($claim.claim_text.SubString(0, [Math]::Min(30, $claim.claim_text.Length)))..." -ForegroundColor DarkGray
    
    # Consult Global Truth
    $grounding = & $triadConsult -RootPath $RootPath -ClaimText $claim.claim_text
    
    # Enrich record
    $claim.claim_id = $grounding.claim_id
    $claim.epistemic_status = $grounding.epistemic_status
    $claim.status_confidence = $grounding.status_confidence
    $claim.status = "GROUNDED"
    $claim.grounded_at = (Get-Date).ToUniversalTime().ToString("o")
    
    # Save to Enriched Log
    $claim | ConvertTo-Json -Compress | Add-Content $EnrichedPath -Encoding UTF8
    $enrichedCount++
}

# 2. Update Source Log (Simple rewrite for v1)
$allClaims | ForEach-Object { $_ | ConvertTo-Json -Compress } | Set-Content $LogPath -Encoding UTF8

Write-Host "[MP02] Grounded $enrichedCount model claims." -ForegroundColor Cyan
