<#
.SYNOPSIS
  T35_RunCampaign.ps1
  Node 3.2 Bounded Campaign Runner.
  Executes a single-shot agentic campaign transaction.

.PARAMETER CampaignFile
  Path to campaign config json.
.PARAMETER DryRun
  If set, just checks logic.
#>

param(
    [string]$CampaignFile = "D:\Infinite\Infinity\Runtime\Autonomy\campaigns\campaign_first_contact_recovery.json",
    [switch]$DryRun
)

$T34 = "D:\Infinite\Infinity\Truth_Engine\T34_ReplayAutonomy.ps1"
$T31 = "D:\Infinite\Infinity\Truth_Engine\T31_ProposeIntents.ps1"
$T32 = "D:\Infinite\Infinity\Truth_Engine\T32_EnqueueFromProposals.ps1"
$T08 = "D:\Infinite\Infinity\Runtime\Decision\T08_Executor.ps1"
$T20 = "D:\Infinite\Infinity\Truth_Engine\T20_VerifyReceipts.ps1"
$Ledger = "D:\Infinite\Infinity\Runtime\Receipts\Receipt_Ledger.jsonl"

function Log($msg, $color = "White") { Write-Host "[Campaign] $msg" -ForegroundColor $color }

if (-not (Test-Path $CampaignFile)) { Write-Error "Config not found: $CampaignFile"; return }
$camp = Get-Content $CampaignFile -Raw | ConvertFrom-Json

if (-not $camp.enabled) { Log "Campaign Disabled." "Yellow"; return }

# 1. Global Autonomy Check
Log "Checking Global Perms..."
$perms = & $T34 | ConvertFrom-Json
if (-not $perms.enforce.enqueue_allowed) {
    Log "Global Autonomy Locked: $($perms.reason)" "Red"
    return
}
Log "Global Mode: $($perms.effective_mode)" "Cyan"

# 2. Campaign Budget Check (PS 5.1 safe JSONL scan)
Log "Checking Campaign Budget..."

if (Test-Path $Ledger) {
    $since = (Get-Date).AddMinutes( - [int]$camp.constraints.window_minutes).ToUniversalTime()
    $intentId = [string]$camp.intent_template.intent_id
    $max = [int]$camp.constraints.max_enqueues_per_window

    $count = 0
    $lines = Get-Content $Ledger -Tail 2000

    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }

        $obj = $null
        try { $obj = $line | ConvertFrom-Json } catch { continue }
        if (-not $obj) { continue }

        # ts parse
        $ts = $null
        try { $ts = [DateTimeOffset]::Parse([string]$obj.ts).ToUniversalTime() } catch { continue }
        if ($ts -lt $since) { continue }

        # intent match (support both top-level intent_id or nested)
        $objIntent = $null
        if ($obj.PSObject.Properties.Name -contains "intent_id") { $objIntent = [string]$obj.intent_id }
        if ($objIntent -ne $intentId) { continue }

        # classify attempt (support schema variants)
        $isAttempt = $false

        # Variant A: top-level type == "ATTEMPT"
        if ($obj.PSObject.Properties.Name -contains "type" -and ([string]$obj.type -eq "ATTEMPT")) { $isAttempt = $true }

        # Variant B: receipt container with receipt.type == "ATTEMPT"
        if (-not $isAttempt -and $obj.PSObject.Properties.Name -contains "receipt" -and $obj.receipt) {
            $rt = $null
            if ($obj.receipt.PSObject.Properties.Name -contains "type") { $rt = [string]$obj.receipt.type }
            if ($rt -eq "ATTEMPT") { $isAttempt = $true }
        }

        if ($isAttempt) {
            $count++
            if ($count -ge $max) { break }
        }
    }

    if ($count -ge $max) {
        Log "Campaign Budget Exhausted ($count >= $max)" "Yellow"
        return
    }
}

# 3. Execution (Bounded)
$tmpl = $camp.intent_template
Log "Executing Campaign Step: $($tmpl.intent_id)" "Green"

if ($DryRun) {
    Log "[DryRun] Would Propose -> Enqueue -> Trigger -> Verify"
    return
}

# A. Propose (With Single-Shot Cleanup)
Log "  -> Proposing..."
$PropFile = "D:\Infinite\Infinity\Runtime\Autonomy\proposed_intents.jsonl"
if (Test-Path $PropFile) { Clear-Content $PropFile }

& $T31 -Title $tmpl.title -ContentPath $tmpl.payload_path -Type $tmpl.type -Target $tmpl.target -SourceDetails "campaign:$($camp.campaign_id)" -ReviewStatus "approved" -CampaignId $camp.campaign_id

# B. Enqueue
Log "  -> Enqueuing..."
& $T32 -CampaignId $camp.campaign_id

# C. Executor (Trigger)
Log "  -> Executor (Trigger)..."
& $T08

# D. Executor (Reap) - wait a moment for local loop
Start-Sleep -Seconds 2
Log "  -> Executor (Reap)..."
& $T08

# E. Verify
Log "  -> Verifying..."
& $T20 -IntentId $tmpl.intent_id -Strict

Log "Campaign Step Complete." "Green"
