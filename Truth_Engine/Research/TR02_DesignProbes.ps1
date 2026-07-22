<# 
.SYNOPSIS
    TR02 Design Probes
.DESCRIPTION
    Maps research targets to specific tool recipes (e.g., EXTERNAL_FETCH via NeuralFetch).
#>

param(
    [string]$PolicyPath = "D:\Infinite\Infinity\Truth_Engine\Research\TE_Research_Policies.json",
    [string]$TargetsPath = "D:\Infinite\Infinity\Truth_Engine\Research\TE_Research_Targets.jsonl",
    [string]$OutputPath = "D:\Infinite\Infinity\Truth_Engine\Research\TE_Research_Probes.jsonl"
)

# 1. Load Policy
if (-not (Test-Path $PolicyPath)) { throw "Policy missing: $PolicyPath" }
$policy = Get-Content $PolicyPath | ConvertFrom-Json
$budgets = $policy.research_policy.budgets

# 2. Load Targets
if (-not (Test-Path $TargetsPath)) {
    Write-Warning "No targets found. Design aborted."
    return
}
$targets = @(Get-Content $TargetsPath | ForEach-Object { $_ | ConvertFrom-Json })

# 3. Design Probes
$existingProbes = if (Test-Path $OutputPath) { @(Get-Content $OutputPath | ForEach-Object { $_ | ConvertFrom-Json }) } else { @() }
$activeProbeTargets = @($existingProbes | Where-Object { $_.status -eq "PENDING" } | Select-Object -ExpandProperty target_claim_id -Unique)

$probes = New-Object System.Collections.Generic.List[PSObject]

foreach ($target in $targets) {
    # Skip if target already has a PENDING probe
    if ($activeProbeTargets -contains $target.claim_id) { continue }
    $type = "EXTERNAL_FETCH" # Default
    $risk = 5
    $params = @{}

    if ($target.current_status -eq "TENUOUS") {
        $type = "HISTORY_SCAN"
        $risk = 3
        $params = @{ depth = "deep"; anchor = $target.claim_id }
    }
    elseif ($target.current_status -eq "UNKNOWN") {
        $type = "EXTERNAL_FETCH"
        $risk = 8
        $params = @{ query = $target.canonical_text; mode = "precise" }
    }

    # Ensure risk doesn't exceed policy
    if ($risk -gt $budgets.max_risk_per_probe) { $risk = $budgets.max_risk_per_probe }

    $ts = (Get-Date).ToUniversalTime().ToString("yyyyMMddHHmmss")
    $probes.Add([PSCustomObject]@{
            probe_id        = "PRB-$($target.claim_id)-$ts-$((Get-Random))"
            target_claim_id = $target.claim_id
            probe_type      = $type
            risk_cost       = $risk
            parameters      = $params
            status          = "PENDING"
        })
}

# 4. Save Probes
$probes | ForEach-Object { $_ | ConvertTo-Json -Compress | Add-Content $OutputPath }

Write-Host "[TR02] Designed $($probes.Count) research probes." -ForegroundColor Cyan
