# Axis_Witness_Scheduler.psm1
# Phase 67: Automated Witness Scheduler
# Orchestrates "Human-in-the-Loop" sovereignty by auto-proposing witnesses on specific triggers.

$SchedulerStatePath = Join-Path $PSScriptRoot "Scheduler_State.json"

function Get-SchedulerState {
    $defaults = @{
        last_run_utc        = [DateTime]::MinValue.ToString("o")
        last_proposal_utc   = [DateTime]::MinValue.ToString("o")
        last_proposed_key   = ""
        tick_id             = 0
        hourly_count        = 0
        hourly_cost_icu     = 0
        current_hour_bucket = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH")
    }

    if (Test-Path $SchedulerStatePath) {
        $disk = Get-Content $SchedulerStatePath | ConvertFrom-Json
        foreach ($key in $defaults.Keys) {
            if ($null -eq $disk.$key) { $disk | Add-Member -MemberType NoteProperty -Name $key -Value $defaults[$key] -Force }
        }
        return $disk
    }
    return [PSCustomObject]$defaults
}

function Save-SchedulerState {
    param($State)
    $State | ConvertTo-Json | Set-Content $SchedulerStatePath
}

function Invoke-WitnessScheduler {
    param(
        [string]$KernelUrl = "http://127.0.0.1:8798",
        [string]$PulseLedgerPath = "D:\Infinite\Infinity\Governance\integrity_pulse_ledger.jsonl",
        [string]$WitnessLedgerPath = "D:\Infinite\Infinity\Governance\Axis_Witness_Ledger.jsonl"
    )

    $state = Get-SchedulerState
    $now = [DateTime]::UtcNow
    $hourBucket = $now.ToString("yyyy-MM-ddTHH")
    $logPath = "D:\Infinite\Infinity\Console\sched_debug.log"

    # Initialize New/Nullable Fields
    if ($null -eq $state.tick_id) { $state.tick_id = 0 }
    if ($null -eq $state.hourly_count) { $state.hourly_count = 0 }
    if ($null -eq $state.hourly_cost_icu) { $state.hourly_cost_icu = 0 }
    if ($null -eq $state.last_proposed_key) { $state.last_proposed_key = "" }
    
    $state.tick_id++

    # 1. Budget Reset
    if ($state.current_hour_bucket -ne $hourBucket) {
        $state.current_hour_bucket = $hourBucket
        $state.hourly_count = 0
        $state.hourly_cost_icu = 0
    }

    # Audit Trace Base
    $audit = [PSCustomObject]@{
        ts_utc         = $now.ToString("o")
        tick_id        = $state.tick_id
        pulse_hash     = "N/A"
        drift_detected = $false
        drift_reason   = "None"
        decision       = "SKIP"
        skip_reason    = "None"
        proposal_id    = $null
        cost_est       = 0
    }

    try {
        # 2. Rate Limits (Hard Cap)
        if ($state.hourly_count -ge 12) { 
            $audit.skip_reason = "hourly_cap"
            return 
        }

        # 3. Read System State (Pulse)
        if (-not (Test-Path $PulseLedgerPath)) { 
            $audit.skip_reason = "pulse_missing"
            return 
        }

        # CONCURRENCY GUARD: Strip BOM and handle partial reads
        $lastPulseJson = Get-Content $PulseLedgerPath -Tail 1 -ErrorAction SilentlyContinue 
        if (-not $lastPulseJson) { 
            $audit.skip_reason = "pulse_empty"
            return 
        }
        $lastPulseJson = $lastPulseJson -replace '^\uFEFF', '' 

        try {
            $pulse = $lastPulseJson | ConvertFrom-Json -ErrorAction Stop
        }
        catch {
            $audit.skip_reason = "pulse_parse_error"
            return
        }

        $audit.pulse_hash = $pulse.hash
        $audit.drift_detected = $pulse.drift_detected
        $audit.drift_reason = $pulse.drift_reason

        # 4. Evaluate Triggers
        $shouldPropose = $false
        $reason = ""

        # Trigger A: Drift (Fact-based, policy-independent)
        if ($pulse.drift_detected -eq $true) {
            # DEDUPE CHECK
            if ($pulse.hash -eq $state.last_proposed_key) {
                $audit.skip_reason = "dedupe_drift"
            }
            else {
                $shouldPropose = $true
                $reason = "Drift: $($pulse.drift_reason)"
            }
        }

        # Trigger B: Cadence (e.g. every 1 hour if no witness)
        if (-not $shouldPropose -and $audit.skip_reason -eq "None") {
            $lastWitnessTime = [DateTime]::MinValue
            if (Test-Path $WitnessLedgerPath) {
                # Strip BOM from ledger line too
                $rawWit = Get-Content $WitnessLedgerPath -Tail 1 -ErrorAction SilentlyContinue
                if ($rawWit) {
                    try {
                        $lastWit = ($rawWit -replace '^\uFEFF', '') | ConvertFrom-Json
                        if ($lastWit.ts_utc) { $lastWitnessTime = [DateTime]::Parse($lastWit.ts_utc) }
                    }
                    catch {}
                }
            }
            
            $minutesSinceWitness = ($now - $lastWitnessTime).TotalMinutes
            if ($minutesSinceWitness -gt 60) {
                # Check for duplicate cadence proposal
                if ($pulse.hash -eq $state.last_proposed_key) {
                    $audit.skip_reason = "dedupe_cadence"
                }
                else {
                    $lastPropTime = [DateTime]::Parse($state.last_proposal_utc)
                    if (($now - $lastPropTime).TotalMinutes -gt 60) {
                        $shouldPropose = $true
                        $reason = "Cadence (Hourly)"
                    }
                    else {
                        $audit.skip_reason = "cadence_wait"
                    }
                }
            }
            else {
                $audit.skip_reason = "no_trigger"
            }
        }

        # 5. Execute Proposal
        if ($shouldPropose) {
            $req = @{
                source_id    = "SCHEDULER"
                selected_key = $pulse.hash
                action       = "WITNESS_EVENT"
                note         = "Auto-generated: $reason"
                tags         = @("auto", "scheduler")
                payload      = @{ pulse = $pulse }
            }

            $resp = Invoke-RestMethod -Uri "$KernelUrl/api/witness/propose" -Method Post -Body ($req | ConvertTo-Json -Depth 5) -ContentType "application/json"
            
            # Update State
            $state.last_proposal_utc = $now.ToString("o")
            $state.last_proposed_key = $pulse.hash
            $state.hourly_count++
            $state.hourly_cost_icu += ($resp.cost_estimate_icu -as [int])
            
            # Update Audit
            $audit.decision = "PROPOSE"
            $audit.skip_reason = "None"
            $audit.proposal_id = $resp.proposal_id
            $audit.cost_est = $resp.cost_estimate_icu
        }
    }
    catch {
        $audit.decision = "ERROR"
        $audit.skip_reason = $_.Exception.Message
        throw $_ # Re-throw for job logging
    }
    finally {
        # SAFE LOGGING: UTF-8 No-BOM (implicit Add-Content)
        try {
            $auditLine = $audit | ConvertTo-Json -Compress
            Add-Content -Path $logPath -Value $auditLine -Encoding utf8 -ErrorAction SilentlyContinue
        }
        catch {}

        # SAFE STATE SAVE
        try {
            $state.last_run_utc = $now.ToString("o")
            Save-SchedulerState $state
        }
        catch {}
    }
}

Export-ModuleMember -Function Invoke-WitnessScheduler
