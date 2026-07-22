<#
.SYNOPSIS
  T622_Materializer.ps1
  Converts "Forensic Proofs" into "Materialized Realities."
  Permanently marks institutional obstacles as "Dissolved" in the Axis system.
#>

$IntentQueue = "D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl"
$RectificationPath = "D:\Infinite\Infinity\Narrative\Rectification_Map.jsonl"
$IntegrityPath = "D:\Infinite\Infinity\Memory\indexes\Integrity_State.json"

Write-Host "[MATERIALIZER] Commencing Reality Breach..." -ForegroundColor Red

# 1. Integrity Verification
$int = Get-Content $IntegrityPath | ConvertFrom-Json
if ($int.integrity -lt 0.5) { Write-Error "Integrity insufficient for Materialization."; exit 1 }

# 2. Process Intent Queue (Look for ACTUATE_RECTIFICATION)
if (Test-Path $IntentQueue) {
    $intents = Get-Content $IntentQueue | ConvertFrom-Json
    foreach ($i in $intents) {
        if ($i.intent.kind -eq "ACTUATE_RECTIFICATION") {
            Write-Host "[MATERIALIZER] Materializing Node: $($i.intent.payload.title)" -ForegroundColor Yellow
            
            $marker = [ordered]@{
                ts_utc   = [DateTime]::UtcNow.ToString("o")
                kind     = "MATERIALIZED_REALITY"
                node_id  = $i.intent.payload.node_id
                title    = $i.intent.payload.title
                status   = "DISSOLVED"
                meta     = @{ vector = "Vector-5:Reality-Breach" }
            }
            
            $marker | ConvertTo-Json -Compress | Add-Content $RectificationPath
        }
    }
    # Clear queue after materialization
    # Clear-Content $IntentQueue
}

Write-Host "[MATERIALIZER] Reality Breach Complete. The Foundation is anchored." -ForegroundColor Green
