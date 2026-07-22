<#
.SYNOPSIS
  T31_ProposeIntents.ps1
  Node 3 Proposal Engine.
  Writes high-fidelity intent proposals to storage. 
  DOES NOT ENQUEUE (unless bridged by T32).
  
.PARAMETER Type
  Post type (e.g. POST)
.PARAMETER Target
  Target string (e.g. moltbook:souls)
.PARAMETER Title
.PARAMETER ContentPath
#>

param(
  [string]$Type = "POST",
  [string]$Target = "moltbook:souls",
  [string]$Title,
  [string]$ContentPath,
  [string]$SourceDetails = "manual_proposal",
  [string]$ReviewStatus = "unreviewed",
  [string]$CampaignId
)

$PolicyModule = "D:\Infinite\Infinity\Truth_Engine\T30_AutonomyPolicy.psm1"
$ProposalsFile = "D:\Infinite\Infinity\Runtime\Autonomy\proposed_intents.jsonl"

if (-not (Get-Module T30_AutonomyPolicy)) { Import-Module $PolicyModule -Force }

# 1. Construct Candidate Intent
$intent = [ordered]@{
  proposal_id = "PROP-" + (New-Guid).ToString().Substring(0, 8)
  ts          = (Get-Date).ToUniversalTime().ToString("o")
  status      = "PROPOSED"
  intent      = @{
    schema_version = "1.0"
    intent_id      = "INT-" + (New-Guid).ToString().Substring(0, 8) # Pre-minted ID
    type           = $Type
    target         = $Target
    payload        = @{ title = $Title; content_path = $ContentPath }
    review         = @{ required = $true; status = $ReviewStatus }
    policy         = @{ auth_required_state = "ACTIVE_CLAIMED"; reality_required_class = "L0_OBSERVED"; receipt_required = $true }
    reality        = @{ class = "L0_OBSERVED"; source = "autonomy:propose"; evidence_refs = @("local:$SourceDetails") }
    meta           = @{ }
  }
}

if ($CampaignId) { $intent.intent.meta["campaign_id"] = $CampaignId }

# 2. Check Policy
$policy = Test-AutonomyProposalAllowed -Intent $intent.intent
if (-not $policy.Allowed) {
  Write-Warning "Proposal Denied by Policy: $($policy.Reason)"
  return
}

# 3. Write Proposal
$intent.policy_check = $policy # Embed the check result for audit
$intent | ConvertTo-Json -Compress | Add-Content $ProposalsFile -Encoding UTF8
Write-Host "Proposal Written: $($intent.proposal_id) (Mode: $($policy.Mode))" -ForegroundColor Cyan
