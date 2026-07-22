<# 
.SYNOPSIS
    Axis Truth Service Wrapper
.DESCRIPTION
    Exposes Truth Engine grounding queries to the Service Mesh.
#>

param(
    [string]$RootPath = "D:\Infinite\Infinity\Truth_Engine",
    [string]$ClaimId,
    [string]$ClaimText,
    [string]$Action = "CONSULT",
    [string]$Caller,
    [object]$Payload,
    [string]$CallId
)

$triadConsult = Join-Path $RootPath "Triad_Consult.ps1"

# If payload is passed via router, extract params
if ($Payload) {
    if ($Payload -is [System.Collections.IDictionary]) {
        if ($Payload.Contains("ClaimId")) { $ClaimId = $Payload["ClaimId"] }
        if ($Payload.Contains("ClaimText")) { $ClaimText = $Payload["ClaimText"] }
        if ($Payload.Contains("Action")) { $Action = $Payload["Action"] }
    }
    else {
        # PSObject / CustomObject
        if ($Payload.ClaimId) { $ClaimId = $Payload.ClaimId }
        if ($Payload.ClaimText) { $ClaimText = $Payload.ClaimText }
        if ($Payload.Action) { $Action = $Payload.Action }
    }
}

switch ($Action) {
    "INGEST" {
        $engine = "D:\Infinite\Axis_Truth_Engine.ps1"
        if (-not (Test-Path $engine)) { return [PSCustomObject]@{ error = "Axis_Truth_Engine not found." } }
        
        # Invoke Engine
        return & $engine -Action "INGEST" -Payload $Payload -RootPath $RootPath
    }

    "CONSULT" {
        if (-not (Test-Path $triadConsult)) {
            return [PSCustomObject]@{ error = "Triad_Consult interface not available at $triadConsult" }
        }
        # Invoke the triad consult script
        $result = & $triadConsult -RootPath $RootPath -ClaimId $ClaimId -ClaimText $ClaimText
        
        # Log usage for TR01
        $usageLog = "D:\Infinite\Infinity\Logs\Truth_Usage_Log.jsonl"
        $logEntry = [ordered]@{
            timestamp = (Get-Date).ToUniversalTime().ToString("o")
            call_id   = $CallId
            claim_id  = $result.claim_id
            status    = $result.epistemic_status
        }
        $logEntry | ConvertTo-Json -Compress | Add-Content $usageLog
        
        return $result
    }
    default {
        return [PSCustomObject]@{ error = "Invalid Action: $Action. Supported: CONSULT" }
    }
}
