# T14_CalibrationObserver.psm1
# Phase 14A: Observes Provenance Log and Computes Prediction Error Stats

function Measure-CalibrationState {
    param()

    $LogPath = "D:\Infinite\Infinity\Runtime\Decision\provenance_events.jsonl"
    $StatePath = "D:\Infinite\Infinity\Runtime\Decision\calibration_state.json"

    if (-not (Test-Path $LogPath)) { return }

    # 1. Read last 2000 events safely (tolerate corrupt lines)
    $events = Read-JsonlTailSafe -Path $LogPath -Tail 2000
    
    # 2. Filter for Resolved Predictions
    $resolved = $events | Where-Object { $_.type -eq "PREDICTION_RESOLVED" }
    
    # Stall Detection
    $lastEventTs = if ($events.Count -gt 0) { $events[-1].ts_utc } else { $null }
    $lastResolvedTs = if ($resolved.Count -gt 0) { $resolved[-1].ts_utc } else { $null }
    
    $status = "observing"
    if ($lastResolvedTs) {
        $ts = [DateTime]::Parse($lastResolvedTs)
        if ((Get-Date).ToUniversalTime() -gt $ts.AddMinutes(30)) {
            $status = "stalled_provenance_write"
        }
    }

    if ($resolved.Count -eq 0) { 
        # No data yet, but write state so generic monitors see 'waiting'
        $state = [ordered]@{ ts_utc = (Get-Date).ToUniversalTime().ToString("o"); status = "waiting_for_data" }
        $state | ConvertTo-Json -Depth 6 | Set-Content $StatePath -Encoding UTF8 -Force
        return 
    }

    # 3. Aggregate Stats
    $totalResolved = $resolved.Count
    $accuracySum = 0
    $deltas = @()
    
    foreach ($r in $resolved) {
        if ($r.data.actual_outcome -eq $r.data.predicted_outcome) { $accuracySum++ }
        if ($null -ne $r.data.duration_delta_ms) { $deltas += [Math]::Abs([double]$r.data.duration_delta_ms) }
    }

    $accuracy = if ($totalResolved -gt 0) { $accuracySum / $totalResolved } else { 0 }
    
    # P95 & Avg
    $avgDurationErr = 0
    $p95DurationErr = 0
    
    if ($deltas.Count -gt 0) {
        $sum = 0; $deltas | ForEach-Object { $sum += $_ }
        $avgDurationErr = $sum / $deltas.Count
        
        $deltas = $deltas | Sort-Object
        $idx = [Math]::Floor(0.95 * ($deltas.Count - 1))
        $p95DurationErr = $deltas[$idx]
    }

    # 4. Construct State
    $state = [ordered]@{
        ts_utc = (Get-Date).ToUniversalTime().ToString("o")
        last_event_ts = $lastEventTs
        status = $status
        
        window_events = $totalResolved
        n_correct = $accuracySum
        accuracy = $accuracy
        
        avg_abs_duration_error_ms = $avgDurationErr
        p95_abs_duration_error_ms = $p95DurationErr
    }

    $state | ConvertTo-Json -Depth 6 | Set-Content $StatePath -Encoding UTF8 -Force
    
    return $state
}

function Read-JsonlTailSafe {
    param(
        [Parameter(Mandatory=$true)][string]$Path,
        [int]$Tail = 1000
    )
    $out = New-Object System.Collections.Generic.List[object]
    foreach ($line in (Get-Content $Path -Tail $Tail -ErrorAction SilentlyContinue)) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try { $out.Add(($line | ConvertFrom-Json -ErrorAction Stop)) } catch { continue }
    }
    return $out
}

Export-ModuleMember -Function Measure-CalibrationState
