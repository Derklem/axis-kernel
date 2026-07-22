<#
.SYNOPSIS
  T32_EnqueueFromProposals.ps1
  Node 3 Bridge. Moves "PROPOSED" -> "ENQUEUED".
  Respects "PROPOSE_ONLY" circuit breakers.
#>

param(
    [switch]$Force,
    [string]$CampaignId
)

$ProposalsFile = "D:\Infinite\Infinity\Runtime\Autonomy\proposed_intents.jsonl"
$QueueFile = "D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl"
$PolicyModule = "D:\Infinite\Infinity\Truth_Engine\T30_AutonomyPolicy.psm1"
$BudgetScript = "D:\Infinite\Infinity\Truth_Engine\T33_AutonomyBudget.ps1"

if (-not (Get-Module T30_AutonomyPolicy)) { Import-Module $PolicyModule -Force }

if (-not (Test-Path $ProposalsFile)) { Write-Warning "No proposals file."; return }

# Read Proposals
$allProposals = Get-Content $ProposalsFile | ConvertFrom-Json
$toProcess = $allProposals | Where-Object { $_.status -eq "PROPOSED" }

if (-not $toProcess) { return }

$processedCount = 0

foreach ($prop in $toProcess) {
    # Campaign Filter
    if ($CampaignId) {
        $metaCamp = if ($prop.intent.meta -and $prop.intent.meta.campaign_id) { $prop.intent.meta.campaign_id } else { $null }
        if ($metaCamp -ne $CampaignId) {
            # Skip unrelated proposals
            continue 
        }
    }

    # Re-Verify Policy (State may have changed since proposal)
    $policy = Test-AutonomyProposalAllowed -Intent $prop.intent
    
    if (-not $policy.Allowed) {
        Write-Warning "Skipping $($prop.proposal_id): $($policy.Reason)"
        continue
    }
    
    if ($policy.Mode -eq "PROPOSE_ONLY" -and -not $Force) {
        Write-Host "Skipping Enqueue (Circuit Breaker Active): $($prop.proposal_id)" -ForegroundColor Yellow
        continue
    }
    
    # ENQUEUE
    # 1. Append to Intent Queue
    # We must ensure intent_queue is a list of intent objects
    $intentObj = $prop.intent
    # Enrich meta
    if (-not $intentObj.meta) { $intentObj | Add-Member -NotePropertyName "meta" -NotePropertyValue @{} -Force }
    $intentObj.meta["proposal_id"] = $prop.proposal_id
    
    $intentObj | ConvertTo-Json -Compress | Add-Content $QueueFile -Encoding UTF8
    
    # 2. Update Proposal Status (In-memory representation for now, or append update event)
    # The file system append-only log model means we can't easily edit the line.
    # Strict Node 3: We should probably write a 'proposal_state.json' or just append a 'status_change' event.
    # For V1 simplicity: We just log it. Real robust impl needs a DB or rewriting the file.
    
    Write-Host "Enqueued: $($intentObj.intent_id) (from $($prop.proposal_id))" -ForegroundColor Green
    $processedCount++
}
