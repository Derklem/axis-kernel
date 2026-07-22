<#
.SYNOPSIS
  T21_Cleanup.ps1
  Auditable Cleanup Utility. Prunes intents from Queue and Execution State with Tombstone Receipts.

.PARAMETER IntentIds
  List of Intent IDs to remove.

.PARAMETER Reason
  Reason for removal (default: "manual_prune").

.PARAMETER DryRun
  If set, only shows what would happen.
#>

param(
    [Parameter(Mandatory = $true)]
    [string[]]$IntentIds,
    [string]$Reason = "manual_prune",
    [switch]$DryRun
)

$Base = "D:\Infinite\Infinity"
$QueueFile = Join-Path $Base "Runtime\Decision\intent_queue.jsonl"
$StateFile = Join-Path $Base "Runtime\Decision\execution_state.json"
$LedgerFile = Join-Path $Base "Runtime\Receipts\Receipt_Ledger.jsonl"

function Snapshot($path) {
    if (Test-Path $path) {
        $ts = (Get-Date).ToUniversalTime().ToString("yyyyMMdd-HHmmss")
        $bak = "$path.$ts.bak.json"
        if ($DryRun) { Write-Host "[DryRun] Would backup $path -> $bak" -ForegroundColor Gray }
        else { Copy-Item $path $bak -ErrorAction SilentlyContinue }
    }
}

# 1. Prune Queue
if (Test-Path $QueueFile) {
    Snapshot $QueueFile
    try {
        $content = Get-Content $QueueFile -Raw | ConvertFrom-Json
        $beforeCount = if ($content -is [array]) { $content.Count } else { 1 }
        
        # Handle Array vs Single Object
        $newQueue = @()
        if ($content -is [array]) {
            $newQueue = $content | Where-Object { $IntentIds -notcontains $_.intent_id }
        }
        elseif ($content -and ($IntentIds -notcontains $content.intent_id)) {
            $newQueue = @($content)
        }

        $afterCount = $newQueue.Count
        $removed = $beforeCount - $afterCount
        
        if ($DryRun) { Write-Host "[DryRun] Queue: Would remove $removed item(s)." -ForegroundColor Yellow }
        else {
            $newQueue | ConvertTo-Json -Depth 10 | Set-Content $QueueFile -Encoding UTF8
            Write-Host "Queue Pruned: -$removed items" -ForegroundColor Green
        }
    }
    catch { Write-Error "Failed to process Queue: $_" }
}

# 2. Prune Execution State
if (Test-Path $StateFile) {
    Snapshot $StateFile
    try {
        $state = Get-Content $StateFile -Raw | ConvertFrom-Json
        
        # Prune Executed
        $newExec = @($state.executed_intents | Where-Object { $IntentIds -notcontains $_ })
        $remExec = $state.executed_intents.Count - $newExec.Count
        if (-not $DryRun) { $state.executed_intents = $newExec }

        # Prune Failed
        $newFail = @($state.failed_intents | Where-Object { $IntentIds -notcontains $_ })
        $remFail = $state.failed_intents.Count - $newFail.Count
        if (-not $DryRun) { $state.failed_intents = $newFail }

        # Prune Inflight (Hashtable)
        $remFlight = 0
        if ($state.inflight) {
            $keys = @($state.inflight.PSObject.Properties.Name)
            foreach ($k in $keys) {
                if ($IntentIds -contains $k) {
                    $remFlight++
                    if (-not $DryRun) { $state.inflight.PSObject.Properties.Remove($k) }
                }
            }
        }

        if ($DryRun) {
            Write-Host "[DryRun] State: Would prune Executed($remExec), Failed($remFail), Inflight($remFlight)" -ForegroundColor Yellow
        }
        else {
            $state | ConvertTo-Json -Depth 5 | Set-Content $StateFile -Encoding UTF8
            Write-Host "State Pruned: Executed(-$remExec), Failed(-$remFail), Inflight(-$remFlight)" -ForegroundColor Green
        }
    }
    catch { Write-Error "Failed to process State: $_" }
}

# 3. Write Tombstones to Ledger
foreach ($id in $IntentIds) {
    if ($DryRun) {
        Write-Host "[DryRun] Would write QUEUE_PRUNED receipt for $id" -ForegroundColor Cyan
    }
    else {
        $evt = [ordered]@{
            ts        = (Get-Date).ToUniversalTime().ToString("o")
            type      = "QUEUE_PRUNED"
            intent_id = $id
            corr_id   = $null
            reason    = $Reason
            meta      = @{ layer = "node2"; confidence = 1.0 }
        }
        $evt | ConvertTo-Json -Compress | Add-Content $LedgerFile -Encoding UTF8
        Write-Host "Tombstone Written: $id" -ForegroundColor Cyan
    }
}
