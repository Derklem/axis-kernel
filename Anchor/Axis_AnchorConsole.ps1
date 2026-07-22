
# Axis_AnchorConsole.ps1
# Phase 80B: Interactive Anchor Console for Outcome Verdicts

$Script:InfinityRoot = "D:\Infinite"
$ErrorActionPreference = "Continue"

# Load dependencies
if (Test-Path "$Script:InfinityRoot\Axis_Outcome.ps1") {
    . "$Script:InfinityRoot\Axis_Outcome.ps1"
} elseif (Test-Path "$Script:InfinityRoot\Infinity\Outcome\Axis_Outcome.ps1") { # handle potential relocations if any
     . "$Script:InfinityRoot\Infinity\Outcome\Axis_Outcome.ps1"
} else {
    # Try root just in case
    . "$Script:InfinityRoot\Axis_Outcome.ps1"
}

if (Test-Path "$Script:InfinityRoot\Infinity\Anchor\Axis_Anchor.ps1") {
    . "$Script:InfinityRoot\Infinity\Anchor\Axis_Anchor.ps1"
}

function Show-AnchorMenu {
    Write-Host ""
    Write-Host "=== AXIS ANCHOR CONSOLE ===" -ForegroundColor Cyan
    Write-Host "1) List pending outcome reviews"
    Write-Host "2) Review next item"
    Write-Host "Q) Quit"
    Write-Host ""
}

function Get-PendingItems {
    $doc = Get-OutcomeInbox
    return @($doc.items) | Where-Object { $_.status -eq "pending" } | Sort-Object run_timestamp_utc
}

function Invoke-ReviewNextItem {
    $items = Get-PendingItems
    if ($items.Count -eq 0) {
        Write-Host "No pending items." -ForegroundColor Gray
        return
    }

    $item = $items[0]
    Write-Host ""
    Write-Host "Feedback ID : $($item.feedback_id)" -ForegroundColor Yellow
    Write-Host "Strategy    : $($item.strategy_id)"
    Write-Host "Pilot       : $($item.pilot_id)"
    Write-Host "Run Time    : $($item.run_timestamp_utc)"
    Write-Host "Proposed    : $($item.proposed_result)"
    if ($item.proposed_notes) {
        Write-Host "Notes       : $($item.proposed_notes)"
    }

    Write-Host ""
    Write-Host "[S] Mark as Success"
    Write-Host "[F] Confirm Failure"
    Write-Host "[W] Mark as Warning"
    Write-Host "[Enter] Skip this item"
    Write-Host ""

    $key = Read-Host "Choice"
    if (-not $key) {
        Write-Host "Skipped." -ForegroundColor Gray
        return
    }

    $verdict = $null
    switch -Regex ($key.ToUpper()) {
        "^S" { $verdict = "success" }
        "^F" { $verdict = "failure" }
        "^W" { $verdict = "warning" }
        default {
            Write-Host "Unknown choice '$key'. Skipped." -ForegroundColor Gray
            return
        }
    }

    $comment = Read-Host "Optional comment"

    OUTCOME-RecordAnchorVerdict -FeedbackId $item.feedback_id -Verdict $verdict -Comment $comment
}

function Invoke-AxisAnchorConsole {
    while ($true) {
        Show-AnchorMenu
        $choice = Read-Host "Select"
        switch ($choice.ToUpper()) {
            "1" {
                $items = Get-PendingItems
                if ($items.Count -eq 0) {
                    Write-Host "No pending items." -ForegroundColor Gray
                } else {
                    Write-Host ""
                    Write-Host "Pending items: $($items.Count)" -ForegroundColor Cyan
                    foreach ($it in $items) {
                        Write-Host "[$($it.feedback_id)] $($it.strategy_id) / proposed=$($it.proposed_result) @ $($it.run_timestamp_utc)"
                    }
                }
            }
            "2" { Invoke-ReviewNextItem }
            "Q" { break }
            default { Write-Host "Unknown option." -ForegroundColor Gray }
        }
    }
}

# Entry point if run directly
if ($MyInvocation.InvocationName -eq ".\Axis_AnchorConsole.ps1" -or
    $MyInvocation.MyCommand.Path -like "*Axis_AnchorConsole.ps1") {
    Invoke-AxisAnchorConsole
}
