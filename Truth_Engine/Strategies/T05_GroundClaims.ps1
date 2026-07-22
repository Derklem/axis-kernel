<# T05 Grounding Layer #>
param([string]$RootPath = "D:\Infinite\Infinity\Truth_Engine")

$ClaimsPath = Join-Path $RootPath "Content\TE_Claims_Index.jsonl"
$GroundingPath = Join-Path $RootPath "Content\TE_Grounding_Ledger.jsonl"

if (-not (Test-Path $ClaimsPath)) { return }

# 1. Load Data
$claims = @(Get-Content $ClaimsPath -Encoding UTF8 | ForEach-Object { if ($_) { $_ | ConvertFrom-Json } } | Where-Object { $null -ne $_ })
if ($claims.Count -eq 0) { return }

# 2. Compute Grounding
$ledger = New-Object System.Collections.Generic.List[PSCustomObject]
foreach ($cl in $claims) {
    # Tally robustly from the claim node
    $P = if ($cl.support.PRIMARY) { [int]$cl.support.PRIMARY } else { 0 }
    $G = if ($cl.support.GROWTH) { [int]$cl.support.GROWTH } else { 0 }
    $I = if ($cl.support.IGNORE) { [int]$cl.support.IGNORE } else { 0 }
    $T = $P + $G + $I
    
    $status = "UNKNOWN"; $reason = "no_data"; $confidence = 0.0
    
    if ($T -gt 0) {
        if ($T -lt 3) { 
            $status = "TENUOUS"; $reason = "insufficient_data"; $confidence = [math]::Min(0.2 + (0.1 * $T), 0.5) 
        }
        elseif ($P -eq 0 -and $G -eq 0 -and $I -ge 3) { 
            $status = "IGNORE_ONLY"; $reason = "no_primary_or_growth_support"; $confidence = [math]::Min(0.1 * $I, 0.7) 
        }
        elseif ($P -ge 3 -and $P -ge $G -and $P -ge $I) {
            if ($I -le ($P + $G)) { $status = "STRONG"; $reason = "primary_dominant"; $confidence = [math]::Min(0.5 + (0.05 * $P), 0.95) }
            else { $status = "PLAUSIBLE"; $reason = "primary_present_ignore_heavy"; $confidence = 0.75 }
        }
        elseif ($P -eq 0 -and $G -ge 3) { 
            $status = "PLAUSIBLE"; $reason = "growth_only"; $confidence = [math]::Min(0.4 + (0.05 * $G), 0.85) 
        }
        else { 
            $status = "PLAUSIBLE"; $reason = "mixed_lattice_presence"; $confidence = 0.6 
        }
    }

    $ledger.Add([PSCustomObject]@{
            claim_id          = $cl.claim_id
            canonical_text    = $cl.canonical_text
            computed_at       = (Get-Date).ToUniversalTime().ToString("o")
            support           = [PSCustomObject]@{ PRIMARY = $P; GROWTH = $G; IGNORE = $I }
            source_roles      = [PSCustomObject]@{ primary_present = ($P -gt 0); growth_present = ($G -gt 0); ignore_dominant = ($I -gt ($P + $G)) }
            structure         = [PSCustomObject]@{ content_count = @($cl.content_ids).Count }
            epistemic_status  = $status
            status_reason     = $reason
            status_confidence = [math]::Round([double]$confidence, 2)
            policy_flags      = [PSCustomObject]@{ needs_human_review = ($status -eq "TENUOUS" -or $I -gt 20); ignore_for_grounding = ($status -eq "IGNORE_ONLY") }
            engine_version    = "T05_v1"
        })
}

if ($ledger.Count -gt 0) {
    $tempPath = "$GroundingPath.tmp"
    $ledger | ForEach-Object { $_ | ConvertTo-Json -Compress -Depth 10 } | Set-Content $tempPath -Encoding UTF8
    Move-Item $tempPath $GroundingPath -Force
}
