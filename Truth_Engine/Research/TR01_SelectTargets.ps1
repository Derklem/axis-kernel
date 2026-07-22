<# 
.SYNOPSIS
    TR01 Select Targets
.DESCRIPTION
    Scans Truth Engine for claims needing research based on usage frequency and grounding status.
#>

param(
    [string]$RootPath = "D:\Infinite\Infinity\Truth_Engine",
    [string]$PolicyPath = "D:\Infinite\Infinity\Truth_Engine\Research\TE_Research_Policies.json",
    [string]$UsageLogPath = "D:\Infinite\Infinity\Logs\Truth_Usage_Log.jsonl",
    [string]$OutputPath = "D:\Infinite\Infinity\Truth_Engine\Research\TE_Research_Targets.jsonl"
)

# 1. Load Policy
if (-not (Test-Path $PolicyPath)) { throw "Policy missing: $PolicyPath" }
$policy = Get-Content $PolicyPath | ConvertFrom-Json
$thresholds = $policy.research_policy.thresholds

# 2. Load Truth Data
$claimsPath = Join-Path $RootPath "Content\TE_Claims_Index.jsonl"
$ledgerPath = Join-Path $RootPath "Content\TE_Grounding_Ledger.jsonl"

if (-not (Test-Path $claimsPath) -or -not (Test-Path $ledgerPath)) {
    Write-Warning "Truth data missing. Selection aborted."
    return
}

$claims = @(Get-Content $claimsPath | ForEach-Object { $_ | ConvertFrom-Json })
$ledger = @(Get-Content $ledgerPath | ForEach-Object { $_ | ConvertFrom-Json })

# 3. Analyze Usage
$usage = @{}
if (Test-Path $UsageLogPath) {
    Get-Content $UsageLogPath | ForEach-Object {
        $log = $_ | ConvertFrom-Json
        if ($log.claim_id) {
            $currentUsage = 0
            if ($usage.Contains($log.claim_id)) { $currentUsage = $usage[$log.claim_id] }
            $usage[$log.claim_id] = $currentUsage + 1
        }
    }
}

# 4. Filter Targets
$targets = New-Object System.Collections.Generic.List[PSObject]
$existingTargets = if (Test-Path $OutputPath) { @(Get-Content $OutputPath | ForEach-Object { $_ | ConvertFrom-Json }) } else { @() }
$activeTargetIds = @($existingTargets | Select-Object -ExpandProperty claim_id -Unique)

foreach ($entry in $ledger) {
    # Skip if claim already has an active target entry (simple de-dupe for v1)
    if ($activeTargetIds -contains $entry.claim_id) { continue }
    $trigger = $false
    $reason = ""

    if ($entry.epistemic_status -eq "TENUOUS" -and $count -ge $thresholds.tenuous_usage_trigger) {
        $trigger = $true
        $reason = "Overused TENUOUS claim ($count usages)"
    }
    elseif ($entry.epistemic_status -eq "UNKNOWN" -and $count -ge $thresholds.unknown_usage_trigger) {
        $trigger = $true
        $reason = "Salient UNKNOWN claim ($count usages)"
    }

    if ($trigger) {
        $claim = $claims | Where-Object { $_.claim_id -eq $entry.claim_id } | Select-Object -First 1
        
        $prio = 1
        if ($entry.epistemic_status -eq "UNKNOWN") { $prio = 2 }

        $targets.Add([PSCustomObject]@{
                timestamp        = (Get-Date).ToUniversalTime().ToString("o")
                claim_id         = $entry.claim_id
                canonical_text   = $entry.canonical_text
                current_status   = $entry.epistemic_status
                usage_count      = $count
                selection_reason = $reason
                priority         = $prio
            })
    }
}

# 5. Save Targets
$targets | ForEach-Object { $_ | ConvertTo-Json -Compress | Add-Content $OutputPath }

Write-Host "[TR01] Selected $($targets.Count) research targets." -ForegroundColor Cyan
