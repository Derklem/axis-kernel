
# Strategy Engine Logic (Phase 63) - Patched V2

# Global/path config
if (-not $Script:InfinityRoot) { $Script:InfinityRoot = "D:\Infinite" }
$Script:StrategyLibraryPath = Join-Path $Script:InfinityRoot "Infinity\Strategies\Strategy_Library.json"
$Script:StrategyLibraryCache = $null
$Script:SimResultsPath = Join-Path $Script:InfinityRoot "Infinity\Simulation_Results.json"

# Load Shadow Bias Functions (Phase 72)
if (Test-Path (Join-Path $Script:InfinityRoot "Infinity\Shadow\Shadow_Bias_Functions.ps1")) {
    . (Join-Path $Script:InfinityRoot "Infinity\Shadow\Shadow_Bias_Functions.ps1")
}
# Load Skills Module (Phase 78)
if (Test-Path (Join-Path $Script:InfinityRoot "Axis_Skills.ps1")) {
    . (Join-Path $Script:InfinityRoot "Axis_Skills.ps1")
}
# Load Outcome Module (Phase 79)
if (Test-Path (Join-Path $Script:InfinityRoot "Axis_Outcome.ps1")) {
    . (Join-Path $Script:InfinityRoot "Axis_Outcome.ps1")
}
# Load Autonomy Gate (Phase 82)
if (Test-Path (Join-Path $Script:InfinityRoot "Axis_AutonomyGate.ps1")) {
    . (Join-Path $Script:InfinityRoot "Axis_AutonomyGate.ps1")
}

function Get-StrategyLibrary {
    if ($Script:StrategyLibraryCache -ne $null) { return $Script:StrategyLibraryCache }
    if (-not (Test-Path -LiteralPath $Script:StrategyLibraryPath)) { return @{ strategies = @() } }
    try {
        $json = Get-Content -LiteralPath $Script:StrategyLibraryPath -Raw -Encoding UTF8
        $lib = $json | ConvertFrom-Json -ErrorAction Stop
        $Script:StrategyLibraryCache = $lib
        return $lib
    }
    catch { return @{ strategies = @() } }
}

function Get-StrategyDefinition {
    param([string]$Id)
    $lib = Get-StrategyLibrary
    return ($lib.strategies | Where-Object { $_.id -eq $Id })
}

function Test-StrategyPreconditions {
    param($StrategyDef, [hashtable]$Context)
    $pre = $StrategyDef.preconditions
    if (-not $pre) { return $true }

    if ($pre.min_log_count) {
        $currentLogCount = 1000 # Stub
        if ($currentLogCount -lt [int]$pre.min_log_count) { return $false }
    }
    if ($pre.last_run_hours) {
        if ($Context.last_run_utc) {
            $lastRun = Get-Date $Context.last_run_utc
            if ((Get-Date) -lt $lastRun.AddHours([int]$pre.last_run_hours)) { return $false } 
        }
    }
    return $true
}

function Invoke-StrategySimulation {
    param($StrategyDef, [hashtable]$Context)
    $model = $StrategyDef.simulation_model
    
    $shadowInfo = ""
    if ($Context -and $Context.risk_snapshot) {
        $bands = $Context.risk_snapshot.bands
        if ($bands) {
            try {
                $pairs = $bands.PSObject.Properties | ForEach-Object { "$($_.Name)=$($_.Value)" }
                $shadowInfo = " | ShadowBands: " + ($pairs -join ", ")
            }
            catch { 
                # Fallback if hashtable vs object
                $pairs = $bands.Keys | ForEach-Object { "$_=$($bands[$_])" }
                $shadowInfo = " | ShadowBands: " + ($pairs -join ", ")
            }
        }
    }

    if (-not $model -or $model -eq "none") {
        return @{ model = $model; simulated = $false; notes = "No model defined." + $shadowInfo; risk_delta = 0 }
    }
    
    # Stub Models
    switch -Regex ($model) {
        "sim_log_impact" { return @{ model = $model; simulated = $true; risk_delta = -0.1; notes = "Low impact." + $shadowInfo } }
        "sim_net_impact" { return @{ model = $model; simulated = $true; risk_delta = 0.0; notes = "Passive scan." + $shadowInfo } }
        "sim_cpu_impact" { return @{ model = $model; simulated = $true; risk_delta = 0.1; notes = "CPU spike acceptable." + $shadowInfo } }
        "sim_neural_load" { return @{ model = $model; simulated = $true; risk_delta = 0.0; notes = "Neural Load Safe" + $shadowInfo } }
        "sim_neural_risk" { return @{ model = $model; simulated = $true; risk_delta = 0.1; notes = "Neural Risk Check Passed" + $shadowInfo } }
        "sim_neural_disk" { return @{ model = $model; simulated = $true; risk_delta = 0.0; notes = "Disk Impact Negligible" + $shadowInfo } }
        default { return @{ model = $model; simulated = $false; risk_delta = 0.2; notes = "Unknown model." + $shadowInfo } }
    }
}

function Process-24_3 {
    param($PendingStrategyInstances, $SimulationResultsPath)
    
    $results = @()
    
    foreach ($instance in $PendingStrategyInstances) {
        # Use library_id as canonical
        $id = $instance.library_id
        if (-not $id) {
            if ($instance.strategy_id) { $id = $instance.strategy_id }
            else { Mind-Log "STRAT_SIM" "Instance implies no ID. Skipping."; continue }
        }

        $def = Get-StrategyDefinition -Id $id
        if (-not $def) { Mind-Log "STRAT_SIM" "Strategy '$id' not found."; continue }
        
        $ctx = if ($instance.context) { $instance.context } else { @{} }
        
        # Attach Shadow risk snapshot if not already provided (Phase 70 Integration)
        if (-not $ctx.ContainsKey("risk_snapshot")) {
            try {
                if (-not (Get-Command Get-ShadowRiskSummary -ErrorAction SilentlyContinue)) {
                    # Try to load if missing, though Neural_Tools should have handled it
                    if (Test-Path (Join-Path $Script:InfinityRoot "Infinity\Shadow\Shadow_Tools.ps1")) {
                        . (Join-Path $Script:InfinityRoot "Infinity\Shadow\Shadow_Tools.ps1")
                    }
                }
                if (Get-Command Get-ShadowRiskSummary -ErrorAction SilentlyContinue) {
                    $shadow = Get-ShadowRiskSummary
                    if ($shadow) {
                        $ctx["risk_snapshot"] = $shadow
                    }
                }
            }
            catch { }
        }
        
        if (-not (Test-StrategyPreconditions -StrategyDef $def -Context $ctx)) {
            $results += @{
                strategy_id = $id
                status      = "preconditions_failed"
                risk_class  = $def.risk_class
                autonomy    = $def.autonomy_level
                simulation  = $null
                context     = $ctx
                instance_id = $instance.id 
            }
            continue
        }
        
        $simResult = Invoke-StrategySimulation -StrategyDef $def -Context $ctx
        
        # Phase 72: Bias Annotation
        $bias = $null
        if (Get-Command Get-ShadowBiasState -ErrorAction SilentlyContinue) {
            # Ideally calculate state once outside loop, but for robustness inside:
            $biasState = Get-ShadowBiasState
            $bias = Get-StrategyBiasAnnotation -StrategyDef $def -BiasState $biasState
        }

        $results += @{
            execution_id = "EXEC-$((Get-Date).ToString('yyyyMMdd-HHmmss'))-$(-join (1..6 | ForEach-Object { [char](Get-Random -InputObject (48..57 + 65..90)) }))"
            strategy_id  = $id
            status       = "simulated"
            risk_class   = $def.risk_class
            autonomy     = $def.autonomy_level
            simulation   = $simResult
            context      = $ctx
            instance_id  = $instance.id 
            shadow_bias  = $bias
        }
    }
    
    if ($results.Count -gt 0) {
        $results | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $SimulationResultsPath -Encoding UTF8
        Mind-Log "STRAT_SIM" "Simulated $($results.Count) strategies."
    }
}

function Process-SimulationEvaluator {
    param($SimulationResultsPath)
    if (-not (Test-Path $SimulationResultsPath)) { return }
    
    $results = Get-Content $SimulationResultsPath -Raw | ConvertFrom-Json
    $results = @($results) # Normalize to array

    $changed = $false
    
    for ($i = 0; $i -lt $results.Count; $i++) {
        $rec = $results[$i]
        if ($rec.status -eq "simulated") {
            # Evaluate
            $approved = $false
            if ($rec.risk_class -eq "low" -and $rec.autonomy -eq "auto") { $approved = $true }
            
            # Phase 14: Self-Model Deference
            $selfModelPath = "D:\Infinite\Infinity\Cortex\Self_Model.json"
            if (Test-Path $selfModelPath) {
                $selfModel = Get-Content $selfModelPath -Raw | ConvertFrom-Json
                $comp = $selfModel.competence_map."$($rec.strategy_id)"
                if ($comp -and $comp.confidence -lt 0.3) {
                    $rec.status = "deferred_low_confidence"
                    $approved = $false
                }
            }
            
            # Phase 72: Soft Deferral (Shadow Bias)
            if ($approved -and $rec.shadow_bias) {
                $bias = $rec.shadow_bias
                # Determine global mode from bias labels or re-fetch state? 
                # Bias object has 'background_hint' and labels like 'global_critical'
                # Check for critical label in labels list
                $isCritical = $bias.bias_labels -contains "global_critical"
                
                if ($isCritical -and $bias.background_hint -eq $true) {
                    $rec.status = "deferred_for_risk"
                    $approved = $false
                }
            }

            # Phase 78: Competence Calibration Check
            if ($approved) {
                if (Get-Command SKILL-GetSkillProfile -ErrorAction SilentlyContinue) {
                    $skill = SKILL-GetSkillProfile -StrategyId $rec.strategy_id
                    if ($skill -and $skill.autonomy_calibrated) {
                        $recLevel = $skill.autonomy_calibrated.recommended_level
                        if ($recLevel -eq "manual" -and $rec.autonomy -eq "auto") {
                            $approved = $false
                            $rec.status = "waiting_approval" # Downgrade to manual flow
                            # Add note? Ideally yes but schema restricts
                        }
                    }
                }
            }

            if ($approved) {
                $rec.status = "approved_for_execution"
            }
            else {
                if ($rec.status -ne "deferred_for_risk") {
                    $rec.status = "waiting_approval"
                }
            }
            $results[$i] = $rec
            $changed = $true
        }
    }
    
    if ($changed) {
        $results | ConvertTo-Json -Depth 10 | Set-Content $SimulationResultsPath -Encoding UTF8
    }
}

function Process-StrategyExecution {
    param($SimulationResultsPath)
    if (-not (Test-Path $SimulationResultsPath)) { return }
    
    $results = Get-Content $SimulationResultsPath -Raw | ConvertFrom-Json
    $results = @($results) # Normalize
    
    $recQueue = $null
    try { $recQueue = Load-JsonSafe (Get-AxisPath "Infinity\Recommendation_Queue.json") } catch {}
    
    for ($i = 0; $i -lt $results.Count; $i++) {
        $rec = $results[$i]
        if ($rec.status -ne "approved_for_execution") { continue }
        
        # Execute
        $def = Get-StrategyDefinition -Id $rec.strategy_id
        if (-not $def) { continue }
        
        # Enforce Autonomy (Phase 82 Gate)
        if (Get-Command GATE-CheckAutonomy -ErrorAction SilentlyContinue) {
            # Phase 15/16: Prediction Generation & Causal Binding
            $predictedSuccess = 0.5
            $selfModelPath = "D:\Infinite\Infinity\Cortex\Self_Model.json"
            if (Test-Path $selfModelPath) {
                $selfModel = Get-Content $selfModelPath -Raw | ConvertFrom-Json
                $comp = $selfModel.competence_map."$($rec.strategy_id)"
                if ($comp) { $predictedSuccess = $comp.success_rate }
            }

            $gate = GATE-CheckAutonomy `
                -StrategyId $def.id `
                -RequestedMode "execute" `
                -Caller "Engine_Functions" `
                -RequestId $rec.execution_id # Phase 16: Strict binding

            # Attach prediction for logging
            $gate.packet | Add-Member -MemberType NoteProperty -Name "predicted_success" -Value $predictedSuccess -Force
            # Ensure execution_id is in packet for forensic trace
            $gate.packet | Add-Member -MemberType NoteProperty -Name "execution_id" -Value $rec.execution_id -Force

            # Phase 16: Durable Prediction Logging
            $predLedgerPath = "D:\Infinite\Infinity\Autonomy\Prediction_Ledger.jsonl"
            $predRecord = [ordered]@{
                execution_id          = $rec.execution_id
                strategy_id           = $def.id
                predicted_success     = $predictedSuccess
                predicted_uncertainty = if ($selfModel.competence_map."$($rec.strategy_id)".uncertainty) { $selfModel.competence_map."$($rec.strategy_id)".uncertainty } else { 0.5 }
                timestamp_utc         = (Get-Date).ToUniversalTime().ToString("o")
            }
            $predRecord | ConvertTo-Json -Compress | Add-Content $predLedgerPath

            if ($gate.decision -eq "escalate") {
                Mind-Log "STRAT_EXEC" "Autonomy Escalated for '$($def.id)'. Reasons: $($gate.packet.reasons -join ', ')"
                continue
            }
            elseif ($gate.decision -eq "deny") {
                Mind-Log "STRAT_EXEC" "Autonomy DENIED for '$($def.id)'. Reasons: $($gate.packet.reasons -join ', ')"
                continue
            }
        }
        else {
            # Fallback to old simple check if gate missing
            switch ($def.autonomy_level) {
                "auto" {}
                "recommend" {
                    if (-not $rec.approved_by_user) { continue }
                }
                default { continue }
            }
        }

        # Execute Actions
        foreach ($action in $def.actions) {
            # Safe Call via Unified Pipeline logic (implied by New-AxisRequest existence in Mind scope)
            # Logic is inside Engine_Functions, so New-AxisRequest needs to be available. 
            # Functions dot-sourced into Mind scope will have access.
            try {
                $reqId = New-AxisRequest -ToolName $action.tool -Args $action.args
                Mind-Log "STRAT_EXEC" "Executed Action $($action.tool) for $($rec.strategy_id) -> $reqId"
            }
            catch {
                Mind-Log "STRAT_EXEC" "Failed execution: $_"
                $actionFailed = $true
            }
        }
        
        # Phase 78: Record Outcome
        if (Get-Command SKILL-RecordOutcome -ErrorAction SilentlyContinue) {
            # Gather Context
            $pilotIdVal = $null
            if (Get-Command Get-PilotContext -ErrorAction SilentlyContinue) {
                $p = Get-PilotContext; if ($p) { $pilotIdVal = $p.current_pilot_id }
            }
            $shadowVal = $null; $shadowModeVal = "normal"
            if (Get-Command Get-ShadowBiasState -ErrorAction SilentlyContinue) {
                $s = Get-ShadowBiasState; if ($s) { $shadowVal = $s.risk_score; $shadowModeVal = $s.mode }
            }
             
            SKILL-RecordOutcome `
                -StrategyId $rec.strategy_id `
                -Result $(if ($actionFailed) { "failure" }else { "success" }) `
                -PilotId $pilotIdVal `
                -ShadowGlobal $(if ($shadowVal) { $shadowVal }else { 0.0 }) `
                -ShadowMode $shadowModeVal `
                -Notes "Engine Execution"

            # Phase 79: Auto-Enqueue for Review?
            # Heuristic: Failures OR High Risk strategies OR New strategies (low run count)
            $shouldAsk = $false
            $res = $(if ($actionFailed) { "failure" }else { "success" }) # Simplification
            if ($res -eq "failure") { $shouldAsk = $true }
            elseif ($def.risk_class -eq "high") { $shouldAsk = $true }
             
            if ($shouldAsk -and (Get-Command OUTCOME-EnqueueForReview -ErrorAction SilentlyContinue)) {
                OUTCOME-EnqueueForReview `
                    -StrategyId $rec.strategy_id `
                    -Result $res `
                    -PilotId $pilotIdVal `
                    -RunTimestampUtc $(Get-Date).ToUniversalTime().ToString("o") `
                    -Notes "Engine auto-flagged for review." `
                    -ExecutionId $rec.execution_id
            }
        }
        
        $rec.status = "executed"
        $results[$i] = $rec
        
        # Mark Queue? (Stub functionality)
    }
    
    $results | ConvertTo-Json -Depth 10 | Set-Content $SimulationResultsPath -Encoding UTF8
}
