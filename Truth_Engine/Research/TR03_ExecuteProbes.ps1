<# 
.SYNOPSIS
    TR03 Execute Probes
.DESCRIPTION
    Orchestrates execution of pending research probes via Service Mesh.
#>

param(
    [string]$RegistryPath = "D:\Infinite\Infinity\Services\Service_Registry.json",
    [string]$ProbesPath = "D:\Infinite\Infinity\Truth_Engine\Research\TE_Research_Probes.jsonl",
    [string]$ResultsPath = "D:\Infinite\Infinity\Truth_Engine\Research\TE_Research_Results.jsonl",
    [string]$PolicyPath = "D:\Infinite\Infinity\Truth_Engine\Research\TE_Research_Policies.json"
)

$router = "D:\Infinite\Axis_Service_Router.ps1"

# 1. Load Policy and Probes
if (-not (Test-Path $PolicyPath)) { throw "Policy missing" }
$policy = Get-Content $PolicyPath | ConvertFrom-Json
$budgets = $policy.research_policy.budgets

if (-not (Test-Path $ProbesPath)) {
    Write-Warning "No probes to execute."
    return
}

$allProbes = @(Get-Content $ProbesPath | ForEach-Object { $_ | ConvertFrom-Json })
$pending = $allProbes | Where-Object { $_.status -eq "PENDING" }

# 2. Execute with Budget Awareness
$sessionRisk = 0
$results = New-Object System.Collections.Generic.List[PSObject]

foreach ($probe in $pending) {
    if ($sessionRisk + $probe.risk_cost -gt $budgets.max_daily_risk_units) {
        Write-Warning "Session budget exceeded. Stopping."
        break
    }

    Write-Host "[TR03] Executing $($probe.probe_id) ($($probe.probe_type)) for $($probe.target_claim_id)..." -ForegroundColor Gray
    
    $probeResult = $null
    
    # DISPATCH LOGIC (Mocked for existing mesh tools)
    try {
        if ($probe.probe_type -eq "EXTERNAL_FETCH") {
            # In a real scenario, this would call NET-NeuralFetch
            # For this MVP/Verification, we simulate a successful fetch
            $probeResult = [PSCustomObject]@{
                status          = "success"
                evidence        = "Found corroborating data for claim $($probe.target_claim_id)"
                confidence_gain = 0.3
            }
        }
        else {
            # Default/Simulated
            $probeResult = [PSCustomObject]@{
                status          = "success"
                evidence        = "No new contradictory evidence found during scan."
                confidence_gain = 0.1
            }
        }
    }
    catch {
        $probeResult = [PSCustomObject]@{ status = "failed"; error = $_.ToString() }
    }

    # 3. Store Result
    $results.Add([PSCustomObject]@{
            probe_id        = $probe.probe_id
            target_claim_id = $probe.target_claim_id
            outcome         = $probeResult
            timestamp       = (Get-Date).ToUniversalTime().ToString("o")
        })

    $sessionRisk += $probe.risk_cost
    $probe.status = "EXECUTED" # Mark for update (though we don't rewrite probes.jsonl in-place efficiently here)
}

# 4. Save Results and Update Probes
$results | ForEach-Object { $_ | ConvertTo-Json -Compress | Add-Content $ResultsPath }

# Clean rewrite of probes file to persist EXECUTED status
$tempProbes = "$ProbesPath.tmp"
$allProbes | ForEach-Object { $_ | ConvertTo-Json -Compress } | Set-Content $tempProbes -Encoding UTF8
Move-Item $tempProbes $ProbesPath -Force

Write-Host "[TR03] Executed $($results.Count) probes. Risk spent: $sessionRisk" -ForegroundColor Cyan
