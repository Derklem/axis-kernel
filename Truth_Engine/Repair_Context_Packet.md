# Truth Engine Repair Context

Here are the exact files requested to fix the Truth Engine wiring.

## A) Truth Orchestration & Router

### 1. `D:\Infinite\Infinity\Truth_Engine\Axis_Truth_Service.ps1`
```powershell
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
```

### 2. `D:\Infinite\Infinity\Truth_Engine\Triad_Consult.ps1`
(Standard Read-Only Script - Confirmed Exists)

### 3. `D:\Infinite\Axis_Service_Router.ps1`
**(Key Excerpt - Lines 100-106)**
```powershell
        # Invoke the agent script with the payload
        if ($ServiceId -eq "TRUTH-CONSULT-001") {
            $result = & $service.provider_script -Action "CONSULT" -Payload $Payload -Caller $Caller -CallId $callId
        }
        else {
            $result = & $service.provider_script -Caller $Caller -Payload $Payload -CallId $callId
        }
```

## B) Strategy Callers & Strategies

### 4. `D:\Infinite\Axis_Input_Architecture.ps1`
**(Key Excerpt - Lines 135-136)**
```powershell
                # Invoke T01 Strategy
                & "D:\Infinite\Infinity\Truth_Engine\Strategies\T01_LogObservation.ps1" -Payload $tePayload
```

### 5. `D:\Infinite\Infinity\Truth_Engine\Strategies\T01_LogObservation.ps1`
**(Broken Recursive Logic)**
```powershell
<# T01 Strategy #>
param([object]$Payload, [string]$RootPath = "D:\Infinite\Infinity\Truth_Engine")
$cleanPayload = [PSCustomObject]@{
    content  = $Payload.Content
    source   = $Payload.Source
    channel  = $Payload.Channel
    location = $Payload.Location
    metadata = $Payload.Metadata
}
# !!! BUG: Recursive Ghost Call !!!
& "D:\Infinite\Axis_Truth_Engine.ps1" -Action "INGEST" -Payload $cleanPayload
<# ... Wrapper Text ... #>
param(
    [object]$Payload,
    [string]$RootPath = "D:\Infinite\Infinity\Truth_Engine"
)
# Call the Truth Engine Core to INGEST
# ...
try {
    # 1. Define Unique Observation ID
    # ...
    # 3. Invoke Core Ingest (Again!)
    & "D:\Infinite\Axis_Truth_Engine.ps1" -Action "INGEST" -Payload $cleanPayload
    # ...
}
catch {
    Write-Error "[STRATEGY:T01] Failed to log observation: $_"
}
```

### 6. `D:\Infinite\Infinity\Truth_Engine\Strategies\T02_ResolveOrigins.ps1`
(Valid Logic - Confirmed)

## C) Data Model Reality
- **TE_Observations_Log.jsonl**: `{"obs_id":"OBS-20260127..."}` (Valid)
- **TE_Content_Nodes.jsonl**: `{"content_id":"CNT-34..."}` (Valid, Schema V1)
- **TE_Origin_Map.jsonl**: `{"edge_id":"ORIGIN-5c..."}` (Valid)

## D) Tenant Policies
`TE_Tenant_Policies.json` exists with strict filters (Lineage: PLAUSIBLE+, Oryn: STRONGonly).
