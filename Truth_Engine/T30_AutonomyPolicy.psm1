<#
.SYNOPSIS
  T30_AutonomyPolicy.psm1
  Node 3 Policy Enforcement Module.
  Wraps Budget check and Config validation.
.FUNCTION Test-AutonomyProposalAllowed
  Input: $Intent (Hashtable)
  Output: [PSCustomObject]@{ Allowed=$bool, Mode=$string, Reason=$string }
#>

$ConfigPath = "D:\Infinite\Infinity\Runtime\Autonomy\autonomy_config.json"
$BudgetScript = "D:\Infinite\Infinity\Truth_Engine\T33_AutonomyBudget.ps1"

function Get-AutonomyConfig {
    if (Test-Path $ConfigPath) {
        return (Get-Content $ConfigPath -Raw | ConvertFrom-Json)
    }
    return $null
}

function Test-AutonomyProposalAllowed {
    param($Intent)
    
    $res = [ordered]@{ Allowed = $false; Mode = "PROPOSE_ONLY"; Reason = "init" }
    
    # 1. Config Check
    $cfg = Get-AutonomyConfig
    if (-not $cfg) { 
        $res.Reason = "config_missing"
        return [pscustomobject]$res 
    }
    
    $globalMode = $cfg.autonomy_mode
    
    # 2. Budget Check (Circuit Breaker)
    $budget = & $BudgetScript | ConvertFrom-Json
    
    # Logic Update: T33 returns allowed=$false if breaker active.
    # We must check if a mode_override permits "PROPOSE_ONLY" before hard blocking.
    if (-not $budget.allowed) {
        if ($budget.mode_override -eq "PROPOSE_ONLY") {
            # Soft Block / Downgrade
            $globalMode = "PROPOSE_ONLY"
        }
        else {
            # Hard Block
            $res.Reason = "budget_denied: $($budget.reason)"
            return [pscustomobject]$res
        }
    }
    
    # Apply override (redundant but safe if allowed=true cases exist)
    if ($budget.mode_override) {
        $globalMode = $budget.mode_override
    }
    
    # 3. Intent Validations (Basic)
    if (-not $Intent) {
        $res.Reason = "null_intent"
        return [pscustomobject]$res
    }
    
    # Policy: No recursion without explicit policy (future)
    # Policy: Require L0 proof if configured
    if ($cfg.constraints.require_l0_proof_for_proposal) {
        # This is a meta-check: does the Agent *claim* to have observed L0?
        # We don't verify the proof here (T17 does that at exec), we verify the *shape*.
        if (-not ($Intent.reality -and $Intent.reality.class -eq "L0_OBSERVED")) {
            $res.Reason = "policy_violation_l0_required"
            return [pscustomobject]$res
        }
    }
    
    $res.Allowed = $true
    $res.Mode = $globalMode
    $res.Reason = "policy_passed"
    
    return [pscustomobject]$res
}

Export-ModuleMember -Function Test-AutonomyProposalAllowed
