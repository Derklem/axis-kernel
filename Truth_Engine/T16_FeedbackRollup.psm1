# T16_FeedbackRollup.psm1
# v0.1 - Blind Spot Analytics
# Analyzes provenance events to measure the delta between Prediction and Reality.

param(
    [string]$ProvenancePath = "D:\Infinite\Infinity\Runtime\Decision\provenance_events.jsonl",
    [string]$OutputPath = "D:\Infinite\Infinity\Runtime\Decision\feedback_summary.json",
    [int]$WindowSize = 500
)

function Get-FeedbackRollup {
    <#
    .SYNOPSIS
        Computes Blind Spot rates from recent provenance events.
    .DESCRIPTION
        Reads the tail of provenance_events.jsonl, filters for PREDICTION_RESOLVED,
        and aggregates statistics on Prediction vs. Actual Outcome.
    #>
    
    if (-not (Test-Path $ProvenancePath)) {
        Write-Warning "T16: Provenance file not found."
        return $null
    }

    $events = Get-Content $ProvenancePath -Tail $WindowSize -ErrorAction SilentlyContinue | 
              ForEach-Object { $_ | ConvertFrom-Json } |
              Where-Object { $_.type -eq "PREDICTION_RESOLVED" }

    if (-not $events) {
        Write-Verbose "T16: No PREDICTION_RESOLVED events in window."
        return $null
    }

    $total = $events.Count
    $blindSpots = 0
    
    $breakdown = @{
        "TruthServiceUnavailable" = 0
        "TruthStatusInsufficient" = 0
        "AuthSentinel"            = 0
        "PolicyBlock"             = 0
        "Other"                   = 0
    }

    foreach ($ev in $events) {
        $data = $ev.data
        
        # Blind Spot Definition: Predicted ALLOW, but Actual BLOCKED
        if ($data.actual_outcome -eq "BLOCKED" -and ($data.predicted_decision -eq "ALLOW" -or $null -eq $data.predicted_decision)) {
            $blindSpots++
            
            $reason = if ($data.block_reason) { $data.block_reason } else { "Other" }
            if ($breakdown.ContainsKey($reason)) {
                $breakdown[$reason]++
            } else {
                $breakdown["Other"]++
            }
        }
    }

    $rate = if ($total -gt 0) { $blindSpots / $total } else { 0 }

    $summary = [ordered]@{
        ts_utc = (Get-Date).ToUniversalTime().ToString("o")
        window_size = $WindowSize
        analyzed_events = $total
        blind_spot_count = $blindSpots
        blind_spot_rate = $rate
        breakdown = $breakdown
    }

    $summary | ConvertTo-Json -Depth 4 | Set-Content $OutputPath
    return $summary
}

Export-ModuleMember -Function Get-FeedbackRollup
