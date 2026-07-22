<# 
.SYNOPSIS
    MP03 Compute Model Profiles
.DESCRIPTION
    Aggregates grounding statistics into per-model epistemic reliability profiles.
#>

param(
    [string]$GroundedLog = "D:\Infinite\Infinity\Truth_Engine\ModelProfiles\TE_Model_Claim_Grounded.jsonl",
    [string]$ProfilePath = "D:\Infinite\Infinity\Truth_Engine\ModelProfiles\TE_Model_Profiles.jsonl",
    [string]$SummaryPath = "D:\Infinite\Infinity\Truth_Engine\ModelProfiles\TE_Model_Summary.json"
)

if (-not (Test-Path $GroundedLog)) {
    Write-Host "[MP03] No grounded claims to aggregate." -ForegroundColor Gray
    return
}

# 1. Load All Grounded Data
$entries = @(Get-Content $GroundedLog | ForEach-Object { $_ | ConvertFrom-Json })
$models = $entries | Select-Object -ExpandProperty model_id -Unique

$profiles = New-Object System.Collections.Generic.List[PSObject]

foreach ($mid in $models) {
    $mEntries = $entries | Where-Object { $_.model_id -eq $mid }
    
    $dist = @{
        STRONG      = ($mEntries | Where-Object { $_.epistemic_status -eq "STRONG" }).Count
        PLAUSIBLE   = ($mEntries | Where-Object { $_.epistemic_status -eq "PLAUSIBLE" }).Count
        TENUOUS     = ($mEntries | Where-Object { $_.epistemic_status -eq "TENUOUS" }).Count
        IGNORE_ONLY = ($mEntries | Where-Object { $_.epistemic_status -eq "IGNORE_ONLY" }).Count
        UNKNOWN     = ($mEntries | Where-Object { $_.epistemic_status -eq "UNKNOWN" }).Count
    }
    
    # Compute avgs for non-zero statuses
    $strongEntries = $mEntries | Where-Object { $_.epistemic_status -eq "STRONG" }
    $avgStrong = if ($strongEntries.Count -gt 0) { ($strongEntries | Measure-Object -Property status_confidence -Average).Average } else { 0 }
    
    $profile = [PSCustomObject]@{
        model_id              = $mid
        claims_emitted        = $mEntries.Count
        status_distribution   = $dist
        reliability_ratio     = [Math]::Round(($dist.STRONG + $dist.PLAUSIBLE) / $mEntries.Count, 3)
        avg_confidence_strong = [Math]::Round($avgStrong, 3)
        last_updated          = (Get-Date).ToUniversalTime().ToString("o")
    }
    $profiles.Add($profile)
}

# 2. Save Profiles and Summary
$profiles | ForEach-Object { $_ | ConvertTo-Json -Compress | Add-Content "$ProfilePath.tmp" }
Move-Item "$ProfilePath.tmp" $ProfilePath -Force

$summary = @{
    generated_at  = (Get-Date).ToUniversalTime().ToString("o")
    model_count   = $models.Count
    leading_model = ($profiles | Sort-Object reliability_ratio -Descending | Select-Object -First 1).model_id
    total_samples = $entries.Count
}
$summary | ConvertTo-Json | Set-Content $SummaryPath

Write-Host "[MP03] Updated profiles for $($models.Count) models." -ForegroundColor Cyan
