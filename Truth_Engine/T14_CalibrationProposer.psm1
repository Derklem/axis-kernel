# T14_CalibrationProposer.psm1
# Phase 14B: Proposes config adjustments based on observed error.

function Propose-CalibrationAdjustments {
    param()
    
    $StatePath = "D:\Infinite\Infinity\Runtime\Decision\calibration_state.json"
    $ProposalPath = "D:\Infinite\Infinity\Runtime\Decision\calibration_proposals.jsonl"
    
    if (-not (Test-Path $StatePath)) { return }
    $state = Get-Content $StatePath -Raw | ConvertFrom-Json
    
    # Thresholds for Action
    if ($state.window_events -lt 10) { return } # Too few samples
    
    # Heuristics for Proposal
    $proposals = @()
    
    # 1. Duration Correction
    if ($state.avg_duration_error_ms -gt 500) {
        $proposals += [ordered]@{
            target = "predictor.duration_multiplier"
            suggested_delta = 0.1 # Increase estimate
            justification = "High duration underestimate (Avg error: $($state.avg_duration_error_ms)ms)"
        }
    }
    
    # 2. Write Proposals
    foreach ($p in $proposals) {
        $p["id"] = [Guid]::NewGuid().ToString()
        $p["ts"] = (Get-Date).ToUniversalTime().ToString("o")
        $p["status"] = "open"
        
        $p | ConvertTo-Json -Compress | Add-Content $ProposalPath -Encoding UTF8
        
        # Log to Provenance (Optional/Advanced)
        # Write-ProvenanceEvent -Type "CALIBRATION_PROPOSAL_EMITTED" ...
    }
}

Export-ModuleMember -Function Propose-CalibrationAdjustments
