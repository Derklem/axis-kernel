
# Axis_Curriculum.ps1
# Phase 81: Curriculum Engine (Self-Directed Practice)

$Script:InfinityRoot = "D:\Infinite"
$Script:CurriculumPath = "$Script:InfinityRoot\Infinity\Skills\Skill_Curriculum.json"
$Script:TrainingQueuePath = "$Script:InfinityRoot\Infinity\Skills\Skill_Training_Queue.json"

# Load Dependencies
if (Test-Path "$Script:InfinityRoot\Axis_Skills.ps1") { . "$Script:InfinityRoot\Axis_Skills.ps1" }
if (Test-Path "$Script:InfinityRoot\Infinity\Shadow\Shadow_Bias_Functions.ps1") { . "$Script:InfinityRoot\Infinity\Shadow\Shadow_Bias_Functions.ps1" }

function CURRIC-GetSkillCurriculumConfig {
    if (-not (Test-Path $Script:CurriculumPath)) { return $null }
    try { return Get-Content -Raw $Script:CurriculumPath | ConvertFrom-Json } catch { return $null }
}

function CURRIC-GetTrainingQueue {
    if (-not (Test-Path $Script:TrainingQueuePath)) {
        return @{ version=1; queue_id="AXIS-SKILL-TRAINING-QUEUE-RECOVER"; items=@() }
    }
    try { return Get-Content -Raw $Script:TrainingQueuePath | ConvertFrom-Json } catch { return @{ version=1; items=@() } }
}

function CURRIC-SaveTrainingQueue($q) {
    try {
        $q.generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        $q | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:TrainingQueuePath -Encoding UTF8
    } catch { Write-Error "CURRIC: Save failed. $_" }
}

function CURRIC-AnalyzeSkillGaps {
    <#
    .SYNOPSIS
        Identify strategies that should be scheduled for training.
    #>
    param(
        [int]$MinRunsThreshold = 5
    )

    $curr = CURRIC-GetSkillCurriculumConfig
    if (-not $curr) { Write-Warning "CURRIC: No policy found."; return @() }
    
    $candidates = @()
    foreach ($pol in $curr.skills) {
        if (-not $pol.enabled) { continue }
        
        $prof = SKILL-GetSkillProfile -StrategyId $pol.strategy_id
        $runs = 0
        $failRate = 0.0
        
        if ($prof) {
            $runs = $prof.stats.runs_total
            if ($runs -gt 0) { $failRate = $prof.stats.runs_failure / $runs }
        }
        
        $reason = $null
        $pri = 0.5
        
        if ($runs -lt $MinRunsThreshold) {
            $reason = "low_runs"
            $pri += 0.2
        } elseif ($failRate -gt 0.2) {
             $reason = "high_failure_rate"
             $pri += 0.3
        }
        
        if ($reason) {
            $candidates += [ordered]@{
                strategy_id = $pol.strategy_id
                reason = $reason
                priority = $pri
                preferred_mode = $pol.preferred_mode
                requested_runs = if ($pol.max_daily_training_runs) { 1 } else { 1 } # conservative
            }
        }
    }
    
    return $candidates
}

function CURRIC-BuildTrainingQueue {
    <#
    .SYNOPSIS
        Build or refresh the Skill Training Queue based on current gaps and risk.
    #>
    param()

    # 1. Check Risk
    if (Get-Command Get-ShadowBiasState -ErrorAction SilentlyContinue) {
        $shadow = Get-ShadowBiasState
        if ($shadow.global_mode -in @("elevated","critical")) {
            Write-Warning "CURRIC: Shadow mode $($shadow.global_mode) prevents scheduling."
            return
        }
    }

    # 2. Analyze
    $gaps = CURRIC-AnalyzeSkillGaps

    # 3. Build Queue
    $queue = CURRIC-GetTrainingQueue
    
    # Simple append for now (deduplication logic omitted for brevity but recommended)
    # We clear pending items that haven't started to refresh priorities
    $existingRunning = @($queue.items) | Where-Object { $_.status -eq "running" }
    
    $newItems = @()
    foreach ($gap in $gaps) {
        # Check if already running
        if ($existingRunning.strategy_id -contains $gap.strategy_id) { continue }
        
        $newItems += [ordered]@{
            training_id = "TRN-{0}-{1}" -f (Get-Date -Format "yyyyMMdd"), ($gap.strategy_id -replace "[^A-Za-z0-9]","")
            strategy_id = $gap.strategy_id
            mode = $gap.preferred_mode
            reason = $gap.reason
            priority = $gap.priority
            requested_runs = $gap.requested_runs
            runs_completed = 0
            status = "pending"
            shadow_snapshot = $null # captured at run time
        }
    }

    # Merge running + new
    $queue.items = $existingRunning + $newItems
    
    CURRIC-SaveTrainingQueue $queue
    Write-Host "CURRIC: Queue built. $($newItems.Count) new items." -ForegroundColor Cyan
}

Export-ModuleMember -Function CURRIC-AnalyzeSkillGaps, CURRIC-BuildTrainingQueue, CURRIC-GetTrainingQueue
