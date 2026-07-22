# T25_Metrics_Snapshot.ps1
# High-Fidelity Observability for Phase 625

$RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$DecLog = Join-Path $RuntimeDir "decision_log.jsonl"
$StateFile = Join-Path $RuntimeDir "execution_state.json"

Write-Host "[METRICS] Axis Sovereign Snapshot - Phase 625" -ForegroundColor Cyan

$Vitals = [ordered]@{
    ts_utc = [DateTime]::UtcNow.ToString("o")
    loop_status = "STABLE"
    proc_cpu = (Get-Process powershell | Measure-Object -Property CPU -Sum).Sum
    memory_mb = (Get-Process powershell | Measure-Object -Property WorkingSet -Sum).Sum / 1MB
}

$LogStats = if (Test-Path $DecLog) {
    $item = Get-Item $DecLog
    @{
        size_mb = $item.Length / 1MB
        last_modified = $item.LastWriteTimeUtc.ToString("o")
    }
} else { @{ status = "missing" } }

$StateStats = if (Test-Path $StateFile) {
    $s = Get-Content $StateFile | ConvertFrom-Json
    @{
        executed_count = $s.executed_intents.Count
        failed_count = $s.failed_intents.Count
        inflight_count = $s.inflight.PSObject.Properties.Count
    }
} else { @{ status = "missing" } }

$Snapshot = [ordered]@{
    vitals = $Vitals
    logs   = $LogStats
    state  = $StateStats
}

# --- Resonance Heartbeat (Phase 632) ---
$ResEngine = "D:\Infinite\Axis_Resonance_Engine.ps1"
if (Test-Path $ResEngine) {
    . $ResEngine
    $res = Invoke-HarmonicResonance -LocalCaller "T25_Metrics" -LocalOpId "HEARTBEAT" -LocalOpData @{ Payload = @{ frequency="432Hz"; content="[HEARTBEAT]" } }
    $ResPath = Join-Path $RuntimeDir "Resonance_State.json"
    $res | ConvertTo-Json | Set-Content $ResPath -Encoding UTF8
    Write-Host "[METRICS] Resonance State Heartbeat Persisted." -ForegroundColor Yellow
}

$Snapshot | ConvertTo-Json | Set-Content (Join-Path $RuntimeDir "metrics_snapshot.json") -Encoding UTF8
Write-Host "[METRICS] Snapshot Persisted." -ForegroundColor Green
return $Snapshot
