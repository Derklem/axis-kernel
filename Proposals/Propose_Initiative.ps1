<#
.SYNOPSIS
    Generates Initiative Proposals based on System State.
    MANUAL TRIGGER ONLY.
.DESCRIPTION
    Analyzes telemetry, drift, and system state to propose "Read-Only" or "Observation" actions.
    Does NOT execute anything. Writes to `initiative_proposals.jsonl`.
    Constraints:
    - Max 3 proposals.
    - Risk Units <= 1.
    - Categories: READ_ONLY, OBSERVATION.
#>

param(
    [switch]$Force
)

$ProposalFile = "D:\Infinite\Infinity\Proposals\initiative_proposals.jsonl"
$AnalyticsPath = "D:\Infinite\Infinity\Runtime\Decision\execution_analytics.json"

# --- 1. Analyze State ---
$DriftStatus = "UNKNOWN"
$Efficiency = 0.0

if (Test-Path $AnalyticsPath) {
    $a = Get-Content $AnalyticsPath -Raw | ConvertFrom-Json
    $DriftStatus = $a.drift_status
    $Efficiency = $a.autonomy_efficiency
}

$Proposals = @()

# --- 2. Generate Logic (Rule-Based for now) ---

# Rule A: If Drift Detected -> Propose Detailed Scan
if ($DriftStatus -eq "DRIFT_DETECTED") {
    $Proposals += [ordered]@{
        category             = "OBSERVATION"
        summary              = "Perform Deep Drift Scan"
        rationale            = "Drift detected in earth.describe. Need detailed breakdown."
        estimated_risk_units = 0.5
        preconditions        = @("Drift Alert Active")
    }
}

# Rule B: If Efficiency low (high waste) -> Propose Diagnostic
# (Placeholder logic as efficiency is currently 0.0/Started)

# Rule C: General Situational Awareness (Low Priority)
# Only if we track new files or external signals (future)

# Rule D: Default/Demo Proposal (If Force is on, or just to show capability)
# For Phase 608, we will generate a valid READ_ONLY proposal if the list is empty, 
# just to demonstrate the schema, *if* the system feels "blind".
# But following "Restraint", we probably shouldn't propose unless necessary.
# Let's propose 'git status' if we don't have it tracked, as a safe Read-Only expansion.

$current_caps = (Get-Content "D:\Infinite\Infinity\Earth\Earth_Capabilities.json" -Raw | ConvertFrom-Json).capabilities
if (-not ($current_caps.id -contains "git.status")) {
    $Proposals += [ordered]@{
        category             = "READ_ONLY"
        summary              = "Add git.status capability"
        rationale            = "Increase awareness of version control state without mutation."
        estimated_risk_units = 1.0
        preconditions        = @("Sandbox Available")
    }
}


# --- 3. Filter & Write ---
$MaxProposals = 3
$FinalProposals = $Proposals | Select-Object -First $MaxProposals

if ($FinalProposals.Count -eq 0) {
    Write-Host "No aligned proposals at this time." -ForegroundColor Cyan
    exit
}

$CurrentContent = Get-Content $ProposalFile -Raw | ConvertFrom-Json
$Entries = $CurrentContent.entries # Array

foreach ($p in $FinalProposals) {
    $id = "P-{0}-{1:0000}" -f (Get-Date -Format "yyyyMMdd"), (Get-Random -Minimum 1 -Maximum 9999)
    
    $entry = [ordered]@{
        proposal_id          = $id
        ts_utc               = (Get-Date).ToUniversalTime().ToString("o")
        category             = $p.category
        summary              = $p.summary
        rationale            = $p.rationale
        estimated_risk_units = $p.estimated_risk_units
        preconditions        = $p.preconditions
        evidence_refs        = @("earth.describe", "execution_analytics.json")
        confidence           = 0.8 # Static confidence for rule-based
        scope                = "PROPOSAL_ONLY"
        status               = "PENDING"
    }
    
    # Add to in-memory list
    $Entries += $entry
    Write-Host "Generated Proposal: $($entry.proposal_id) ($($entry.summary))" -ForegroundColor Green
}

# Save back
$CurrentContent.entries = $Entries
$CurrentContent | ConvertTo-Json -Depth 5 | Set-Content $ProposalFile -Force
