

function Measure-ExecutionAnalytics {
    param(
        [string]$DecLogPath = "D:\Infinite\Infinity\Runtime\Decision\decision_log.jsonl",
        [string]$OutputPath = "D:\Infinite\Infinity\Runtime\Decision\execution_analytics.json",
        [string]$RollupPath = "D:\Infinite\Infinity\Runtime\Decision\execution_analytics_rollup.jsonl",
        [int]$TailLines = 500
    )

    if (-not (Test-Path $DecLogPath)) { return }

    $logEntries = Get-Content $DecLogPath -Tail $TailLines | ConvertFrom-Json -ErrorAction SilentlyContinue
    if (-not $logEntries) { return }

    # Window: consider entries from the last minute for "Current Pulse" stats
    $now = (Get-Date).ToUniversalTime()
    $windowStart = $now.AddMinutes(-1)
    
    $recent = $logEntries | Where-Object { [DateTime]::Parse($_.ts) -ge $windowStart }

    # Metrics
    $stats = [ordered]@{
        ts_utc               = $now.ToString("o")
        window_seconds       = 60
        total_intents        = 0
        executed_success     = 0
        executed_fail        = 0
        blocked              = 0
        
        # New Telemetry
        autonomy_efficiency  = 0.0
        blockage_breakdown   = @{
            policy  = 0
            adapter = 0
            reality = 0
            other   = 0
        }
        latency_breakdown    = @{
            p95_execution_ms = 0
        }
        capability_histogram = @{}
        drift_status         = "UNKNOWN"
    }

    # Counts
    $stats.total_intents = $recent.Count
    $stats.executed_success = ($recent | Where-Object { $_.result -eq "EXEC_SUCCESS" }).Count
    $stats.executed_fail = ($recent | Where-Object { $_.result -eq "EXEC_FAIL" }).Count
    
    # Blockage Analysis
    $blocked = $recent | Where-Object { $_.result -like "BLOCKED_*" }
    $stats.blocked = $blocked.Count
    
    foreach ($entry in $blocked) {
        switch -Wildcard ($entry.result) {
            "BLOCKED_POLICY*" { $stats.blockage_breakdown.policy++ }
            "BLOCKED_AUTH*" { $stats.blockage_breakdown.policy++ } # Fold Auth into Policy
            "BLOCKED_REALITY" { $stats.blockage_breakdown.reality++ }
            "BLOCKED_UNKNOWN_TOOL" { $stats.blockage_breakdown.adapter++ }
            default { $stats.blockage_breakdown.other++ }
        }
    }

    # Rubric Rubric Logic
    $RulesPath = "D:\Infinite\Infinity\conductor\Autonomy_Efficiency_Rules.json"
    $Rules = if (Test-Path $RulesPath) { Get-Content $RulesPath -Raw | ConvertFrom-Json } else { $null }

    # Classification Counts
    $stats | Add-Member -NotePropertyName "classification_breakdown" -NotePropertyValue @{
        USEFUL  = 0
        NEUTRAL = 0
        WASTE   = 0
    } -Force

    # Scan and Classify
    foreach ($entry in $recent) {
        $class = "NEUTRAL" # Default
        
        # Simple string matching for v1 (Expand to regex if needed via Rules)
        $res = $entry.result

        if ($res -eq "EXEC_SUCCESS" -or $res -eq "DRIFT_DETECTED") { $class = "USEFUL" }
        elseif ($res -like "BLOCKED_*" -or $res -eq "EXEC_FAIL") { $class = "WASTE" }
        elseif ($res -eq "DRY_RUN_TRIGGER") { $class = "NEUTRAL" }
        
        $stats.classification_breakdown[$class]++
    }

    # Autonomy Efficiency = "Useful actions / Total Actions" (Simple Ratio)
    # v2: Could use weights from JSON, for now simple count ratio.
    if ($stats.total_intents -gt 0) {
        $useful = $stats.classification_breakdown.USEFUL
        $stats.autonomy_efficiency = [Math]::Round($useful / $stats.total_intents, 2)
    }

    # Capability Histogram
    $recent | Where-Object { $_.result -eq "EXEC_SUCCESS" -and $_.tool } | Group-Object tool | ForEach-Object {
        $stats.capability_histogram[$_.Name] = $_.Count
    }
    
    # Latency (Duration)
    $durations = $recent | Where-Object { $_.duration_ms } | Select-Object -ExpandProperty duration_ms
    if ($durations) {
        $sorted = $durations | Sort-Object
        $idx = [Math]::Floor($sorted.Count * 0.95)
        $stats.latency_breakdown.p95_execution_ms = $sorted[$idx]
    }

    # Drift Radar (Lightweight Check)
    # Baseline from System Invariants (Phase 603)
    $BaselineHash = "FD6588BE275FF107B3C55F163C500937F44127F5FABE8C39B4E45E8DE1F02D0B"
    
    if (Get-Command Invoke-EarthDescribe -ErrorAction SilentlyContinue) {
        $desc = Invoke-EarthDescribe
        $currentHash = $desc.integrity.adapters_hash
        $stats.drift_status = if ($currentHash -eq $BaselineHash) { "STABLE" } else { "DRIFT_DETECTED" }
    }

    # Write Snapshot
    $stats | ConvertTo-Json -Depth 4 | Set-Content $OutputPath -Force

    # Write Rollup (Compact)
    $stats | ConvertTo-Json -Compress | Add-Content $RollupPath
}

Export-ModuleMember -Function Measure-ExecutionAnalytics
