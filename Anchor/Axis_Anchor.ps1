
# Axis_Anchor.ps1
# Phase 80A: Anchor Review UI & Pending Count

$Script:InfinityRoot        = "D:\Infinite"
$Script:OutcomeInboxPath    = "$Script:InfinityRoot\Infinity\Outcome\Outcome_Feedback_Inbox.json"
$Script:UIOutcomeInboxPath  = "$Script:InfinityRoot\Infinity\UI\UI_Inbox_Outcome_Review.json"

# Optional context modules
if (Test-Path "$Script:InfinityRoot\Infinity\Shadow\Shadow_Bias_Functions.ps1") {
    . "$Script:InfinityRoot\Infinity\Shadow\Shadow_Bias_Functions.ps1"
}
if (Test-Path "$Script:InfinityRoot\Axis_Pilot.ps1") {
    . "$Script:InfinityRoot\Axis_Pilot.ps1"
}

function ANCHOR-GetOutcomeInbox {
    if (-not (Test-Path $Script:OutcomeInboxPath)) {
        return @{
            version          = 1
            inbox_id         = "AXIS-OUTCOME-FEEDBACK-001"
            generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
            items            = @()
        }
    }
    try {
        return Get-Content -Raw -LiteralPath $Script:OutcomeInboxPath | ConvertFrom-Json
    } catch {
        Write-Warning "ANCHOR: Failed to read Outcome_Feedback_Inbox. $_"
        return @{
            version          = 1
            inbox_id         = "AXIS-OUTCOME-FEEDBACK-RECOVER"
            generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
            items            = @()
        }
    }
}

function ANCHOR-BuildUIInboxOutcomeReview {
    <#
    .SYNOPSIS
        Build UI Inbox for pending Anchor outcome reviews.
    #>
    param(
        [int]$MaxCards = 50
    )

    $doc = ANCHOR-GetOutcomeInbox
    $items = @($doc.items) | Where-Object { $_.status -eq "pending" }

    $cards = @()

    # Optional risk snapshot for hint text
    $riskScore = $null
    $riskMode  = $null
    if (Get-Command Get-ShadowBiasState -ErrorAction SilentlyContinue) {
        $rs = Get-ShadowBiasState
        if ($rs) {
            $riskScore = $rs.risk_score
            $riskMode  = $rs.mode
        }
    }

    foreach ($item in $items | Sort-Object run_timestamp_utc -Descending | Select-Object -First $MaxCards) {
        $sid    = [string]$item.strategy_id
        $fid    = [string]$item.feedback_id
        $pilot  = if ($item.pilot_id) { $item.pilot_id } else { "unknown" }
        $ts     = if ($item.run_timestamp_utc) { $item.run_timestamp_utc } else { "unknown" }
        $res    = [string]$item.proposed_result

        $shadowHint = $null
        if ($riskScore -ne $null -and $riskMode) {
            $shadowHint = "Shadow: risk=$riskScore ($riskMode)"
        }

        $cards += [pscustomobject]@{
            card_id        = "OUTCOME-" + ($sid -replace "[^A-Za-z0-9]", "") + "-" + ($fid -replace "[^A-Za-z0-9]", "")
            feedback_id    = $fid
            strategy_id    = $sid
            pilot_id       = $pilot
            proposed_result= $res
            shadow_hint    = $shadowHint
            subtitle       = "Proposed $res @ $ts (pilot=$pilot)"
            status         = "pending"
            actions        = @(
                @{ action_id="anchor_mark_success"; label="Mark as Success"; kind="primary"   ; feedback_id=$fid },
                @{ action_id="anchor_mark_failure"; label="Confirm Failure"; kind="danger"    ; feedback_id=$fid },
                @{ action_id="anchor_mark_warning"; label="Mark as Warning"; kind="secondary"; feedback_id=$fid }
            )
        }
    }

    # Ensure UI dir
    $uiDir = Split-Path $Script:UIOutcomeInboxPath
    if (-not (Test-Path $uiDir)) {
        New-Item -ItemType Directory -Force -Path $uiDir | Out-Null
    }

    $uiDoc = [pscustomobject]@{
        version          = 1
        inbox_id         = "UI-INBOX-OUTCOME-REVIEW"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        cards            = $cards
    }

    $uiDoc | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:UIOutcomeInboxPath -Encoding UTF8

    Write-Host "ANCHOR: UI Outcome Review Inbox built ($($cards.Count) cards)." -ForegroundColor Gray
    return $uiDoc
}

function ANCHOR-GetPendingReviewCount {
    <#
    .SYNOPSIS
        Returns count of pending Anchor outcome reviews.
    #>
    $doc = ANCHOR-GetOutcomeInbox
    $pending = @($doc.items) | Where-Object { $_.status -eq "pending" }
    return ($pending.Count)
}

Export-ModuleMember -Function ANCHOR-BuildUIInboxOutcomeReview, ANCHOR-GetPendingReviewCount
