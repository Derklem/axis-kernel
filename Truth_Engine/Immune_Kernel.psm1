<#
.SYNOPSIS
  Immune Kernel v0.1 (Drift + Quarantine + Reconciliation)
.DESCRIPTION
  - Computes drift score from wrapper/executor signals.
  - Maintains a non-destructive Quarantine state.
  - Runs reconciliation over decision/execution state to heal ghost artifacts.
#>

$script:RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$script:DecLog = Join-Path $script:RuntimeDir "decision_log.jsonl"
$script:StateFile = Join-Path $script:RuntimeDir "execution_state.json"
$script:ApprovalsFile = Join-Path $script:RuntimeDir "approvals.jsonl"
$script:QueueFile = Join-Path $script:RuntimeDir "intent_queue.jsonl"
$script:ImmuneState = Join-Path $script:RuntimeDir "immune_state.json"
$script:TransportState = Join-Path $script:RuntimeDir "transport_state.json"
$script:QuarantineFlag = Join-Path $script:RuntimeDir "quarantine.flag"

function Write-ImmuneEvent {
    param(
        [string]$event,
        [hashtable]$data
    )
    $entry = [ordered]@{
        ts       = (Get-Date).ToUniversalTime().ToString("o")
        decision = "IMMUNE_EVENT"
        event    = $event
    }
    if ($data) {
        foreach ($k in $data.Keys) { $entry[$k] = $data[$k] }
    }
    try { $entry | ConvertTo-Json -Compress | Add-Content $script:DecLog -Encoding UTF8 } catch {}
}

function Get-JsonFile {
    param([string]$path)
    if (-not (Test-Path $path)) { return $null }
    try { return (Get-Content $path -Raw | ConvertFrom-Json) } catch { return $null }
}

function Set-JsonFile {
    param([string]$path, $obj)
    try { $obj | ConvertTo-Json -Depth 8 | Set-Content $path -Encoding UTF8 -Force } catch {}
}

function Get-QuarantineState {
    if (Test-Path $script:QuarantineFlag) { return $true }
    $s = Get-JsonFile $script:ImmuneState
    if ($s -and $s.quarantine -eq $true) { return $true }
    return $false
}

function Set-QuarantineState {
    param([bool]$enabled, [string]$reason = "unspecified")
    $prev = Get-QuarantineState
    if ($enabled) {
        try { "QUARANTINE ON" | Set-Content $script:QuarantineFlag -Encoding UTF8 -Force } catch {}
    }
    else {
        try { if (Test-Path $script:QuarantineFlag) { Remove-Item $script:QuarantineFlag -Force } } catch {}
    }

    $state = Get-JsonFile $script:ImmuneState
    if (-not $state) { $state = [pscustomobject]@{} }

    $state | Add-Member -NotePropertyName "ts" -NotePropertyValue ((Get-Date).ToUniversalTime().ToString("o")) -Force
    $state | Add-Member -NotePropertyName "quarantine" -NotePropertyValue $enabled -Force
    $state | Add-Member -NotePropertyName "reason" -NotePropertyValue $reason -Force

    Set-JsonFile $script:ImmuneState $state

    if ($prev -ne $enabled) {
        Write-ImmuneEvent -event "QUARANTINE_TOGGLE" -data @{
            enabled = $enabled
            reason  = $reason
        }
    }
}

function Get-RecentWrapperLaunches {
    param([int]$tail = 400)
    if (-not (Test-Path $script:DecLog)) { return @() }

    $rows = @()
    foreach ($line in (Get-Content $script:DecLog -Tail $tail)) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        try {
            $o = $line | ConvertFrom-Json
            if ($o -and $o.decision -eq "WRAPPER_LAUNCH") { $rows += $o }
        }
        catch {}
    }
    return $rows
}

function Measure-DriftScore {
    param(
        [string]$executorPath,
        [int]$windowSeconds = 120
    )

    $score = 0
    $signals = @()

    # Signal: executor missing
    if (-not (Test-Path $executorPath)) {
        $score += 100
        $signals += "EXECUTOR_MISSING"
    }
    else {
        # Signal: executor modified very recently
        try {
            $lw = (Get-Item $executorPath).LastWriteTimeUtc
            if (([DateTime]::UtcNow - $lw).TotalSeconds -lt 60) {
                $score += 25
                $signals += "EXECUTOR_RECENTLY_MODIFIED"
            }
        }
        catch {}
    }

    # Signal: multiple wrapper launches in tight window (possible multi-runner)
    $launches = Get-RecentWrapperLaunches -tail 500
    $cutoff = [DateTime]::UtcNow.AddSeconds(-1 * $windowSeconds)
    $recent = $launches | Where-Object {
        try { [DateTime]::Parse($_.ts) -ge $cutoff } catch { $false }
    }

    if ($recent.Count -ge 3) {
        $score += 15
        $signals += "MULTIPLE_WRAPPER_LAUNCHES"
    }

    # Signal: different caller scripts in tight window (ghost + legit runner)
    $callers = @($recent | ForEach-Object { $_.caller_script }) | Where-Object { $_ } | Select-Object -Unique
    if ($callers.Count -ge 2) {
        $score += 20
        $signals += "MULTIPLE_CALLERS"
    }

    return [pscustomobject]@{
        score           = $score
        signals         = $signals
        recent_launches = $recent.Count
        unique_callers  = $callers.Count
    }
}

function Evaluate-Quarantine {
    param(
        [string]$executorPath,
        [int]$enterScore = 60,
        [int]$exitScore = 10
    )

    # 0) Measure drift FIRST (defines $m)
    $m = Measure-DriftScore -executorPath $executorPath

    # 1) Determine quarantine + mode
    $isQ = Get-QuarantineState

    $mode = 0
    if ($isQ) {
        # Flag=True -> Q2 (Block Mutation) for v0.1
        $mode = 2
    }
    elseif ($m.score -ge 20) {
        $mode = 1 # Trace
    }

    # 2) Threshold toggles (may change quarantine flag)
    if (-not $isQ -and $m.score -ge $enterScore) {
        Set-QuarantineState -enabled $true -reason ("drift_score=" + $m.score + " signals=" + ($m.signals -join ","))
        $isQ = $true
        $mode = 2
    }
    elseif ($isQ -and $m.score -le $exitScore) {
        Set-QuarantineState -enabled $false -reason ("drift_score=" + $m.score + " signals=" + ($m.signals -join ","))
        $isQ = $false
        # Recompute mode after exit
        $mode = if ($m.score -ge 20) { 1 } else { 0 }
    }

    # 3) System-of-record writeback (authoritative)
    $state = Get-JsonFile $script:ImmuneState
    if (-not $state) { $state = [pscustomobject]@{} }

    $state | Add-Member -NotePropertyName "ts" -NotePropertyValue ((Get-Date).ToUniversalTime().ToString("o")) -Force
    $state | Add-Member -NotePropertyName "drift_ema" -NotePropertyValue $m.score -Force  # v0.1: raw score as EMA proxy
    $state | Add-Member -NotePropertyName "mode" -NotePropertyValue $mode -Force
    $state | Add-Member -NotePropertyName "quarantine" -NotePropertyValue $isQ -Force

    Set-JsonFile $script:ImmuneState $state

    # 4) Telemetry event
    Write-ImmuneEvent -event "DRIFT_MEASURE" -data @{
        drift_score     = $m.score
        drift_signals   = ($m.signals -join ",")
        recent_launches = $m.recent_launches
        unique_callers  = $m.unique_callers
        quarantine      = $isQ
        mode            = $mode
    }

    return $m
}

function Invoke-Reconciliation {
    param([int]$inflightTimeoutMinutes = 15)

    $state = Get-JsonFile $script:StateFile
    if (-not $state) {
        Write-ImmuneEvent -event "RECONCILE_NO_STATE" -data @{}
        return
    }

    # Normalize inflight to hashtable if needed
    if ($state.inflight -is [System.Management.Automation.PSCustomObject]) {
        $h = @{}
        foreach ($p in $state.inflight.PSObject.Properties) { $h[$p.Name] = $p.Value }
        $state.inflight = $h
    }
    if (-not $state.inflight) { $state | Add-Member -NotePropertyName "inflight" -NotePropertyValue @{} -Force }
    if (-not $state.executed_intents) { $state | Add-Member -NotePropertyName "executed_intents" -NotePropertyValue @() -Force }
    if (-not $state.failed_intents) { $state | Add-Member -NotePropertyName "failed_intents" -NotePropertyValue @() -Force }

    $now = [DateTime]::UtcNow
    $pruned = 0

    # Heal inflight timeouts (convert to failed with reason)
    foreach ($k in @($state.inflight.Keys)) {
        $flight = $state.inflight[$k]
        try {
            $t = [DateTime]::Parse($flight.triggered_ts)
            if ($now -gt $t.AddMinutes($inflightTimeoutMinutes)) {
                $state.failed_intents += $k
                $state.inflight.Remove($k)
                $pruned++

                Write-ImmuneEvent -event "RECONCILE_INFLIGHT_TIMEOUT" -data @{
                    intent_id = $k
                    corr_id   = $flight.corr_id
                    submolt   = $flight.submolt
                }
            }
        }
        catch {}
    }

    # Deduplicate executed/failed arrays
    $state.executed_intents = @($state.executed_intents | Select-Object -Unique)
    $state.failed_intents = @($state.failed_intents   | Select-Object -Unique)

    Set-JsonFile $script:StateFile $state

    Write-ImmuneEvent -event "RECONCILE_DONE" -data @{
        inflight_count = $state.inflight.Count
        pruned         = $pruned
        failed_count   = $state.failed_intents.Count
        executed_count = $state.executed_intents.Count
    }
}


function Evaluate-Transport {
    $state = Get-JsonFile $script:TransportState
    if (-not $state) { return }

    if ($state.status -eq "CRITICAL_PRESSURE") {
        Set-QuarantineState -enabled $true -reason "CRITICAL_QUEUE_PRESSURE"
    }
}

Export-ModuleMember -Function `
    Write-ImmuneEvent, `
    Get-QuarantineState, Set-QuarantineState, `
    Measure-DriftScore, Evaluate-Quarantine, `
    Invoke-Reconciliation, Evaluate-Transport
