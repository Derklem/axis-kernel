function Get-RiskSnapshot {
    param(
        [string]$AxisStatePath = "D:\Infinite\Infinity\Axis_State.json"
    )

    if (-not (Test-Path $AxisStatePath)) {
        return @{
            risk_score     = 0
            open_incidents = 0
            status         = "UNKNOWN"
        }
    }

    try {
        $state = Get-Content $AxisStatePath -Raw | ConvertFrom-Json
        $risk = 0
        $incidents = 0
        
        if ($state.security -and $state.security.risk_ledger) {
            $ledger = $state.security.risk_ledger
            if ($ledger.current_instantaneous_risk) {
                $risk = $ledger.current_instantaneous_risk
            }
            if ($ledger.open_incidents) {
                if ($ledger.open_incidents -is [Array]) { $incidents = $ledger.open_incidents.Count }
                else { $incidents = 1 } # Assume non-empty object is an incident? Or just stick to array count.
                # Spec says 'count > 0'. If it's not an array but exists, it's ambiguous. 
                # Axis_State schema usually arrays.
            }
        }

        # Status Logic (Determinism)
        # ALIVE    = risk_score <= 10 AND open_incidents == 0
        # ELEVATED = risk_score > 10 AND risk_score <= 40 AND open_incidents == 0
        # CRITICAL = risk_score > 40 OR open_incidents > 0

        $status = "ALIVE"
        if ($risk -gt 40 -or $incidents -gt 0) {
            $status = "CRITICAL"
        }
        elseif ($risk -gt 10) {
            $status = "ELEVATED"
        }

        return @{
            risk_score     = $risk
            open_incidents = $incidents
            status         = $status
        }
    }
    catch {
        # Fallback on read error
        return @{
            risk_score     = -1
            open_incidents = -1
            status         = "UNKNOWN"
        }
    }
}
