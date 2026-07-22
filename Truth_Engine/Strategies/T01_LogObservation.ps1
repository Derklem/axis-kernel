<#
.SYNOPSIS
    T01 Log Observation Strategy (Pure)
.DESCRIPTION
    The baseline strategy for Phase T01. 
    Performs raw logging of observations and links to a Content Node.
    Returns { obs_id, content_id } to the caller.
#>

param(
    [object]$Payload,
    [string]$RootPath = "D:\Infinite\Infinity\Truth_Engine"
)

# --- Paths ---
$ObsLog = Join-Path $RootPath "Observation\TE_Observations_Log.jsonl"
$NodesLog = Join-Path $RootPath "Content\TE_Content_Nodes.jsonl"

# --- Helper: Content Hash ---
function Get-ContentHash {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return "EMPTY" }
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return [System.BitConverter]::ToString($hash).Replace("-", "").ToLower()
}

try {
    # 1. Prepare Data
    $now = (Get-Date).ToUniversalTime().ToString("o")
    $obsId = "OBS-" + (Get-Date).ToString("yyyyMMdd-HHmmss-") + (New-Guid).Guid.SubString(0, 8)
    $contentHash = Get-ContentHash -Text $Payload.Content
    
    # 2. Log Observation
    $obsEntry = [ordered]@{
        obs_id    = $obsId
        timestamp = $now
        content   = $Payload.Content
        source    = $Payload.Source
        channel   = $Payload.Channel
        location  = $Payload.Location
        metadata  = $Payload.Metadata
        hash      = $contentHash
    }
    
    if (-not (Test-Path (Split-Path $ObsLog))) { New-Item -ItemType Directory -Path (Split-Path $ObsLog) -Force | Out-Null }
    $obsEntry | ConvertTo-Json -Compress | Add-Content $ObsLog -Encoding UTF8
    
    # 3. Handle Content Node (Deduplication)
    $contentId = $null
    
    # Check if node exists (Naive linear scan for now - T02 optimizes graph later)
    # Ideally should use a Hash Index, but for V1 we append or check linear.
    # Optimization: Just APPEND blindly if we trust T02 to merge? 
    # GPT said "3 raw observations collapsed into 2 unique nodes", implying T01 or T02 dedups.
    # Let's check for existing hash to be clean.
    
    $existingNode = $null
    if (Test-Path $NodesLog) {
        $existingNode = Get-Content $NodesLog -Encoding UTF8 | ForEach-Object { $_ | ConvertFrom-Json } | Where-Object { $_.hash -eq $contentHash } | Select-Object -First 1
    }
    
    if ($existingNode) {
        $contentId = $existingNode.content_id
        # Update last_seen or observation list? 
        # For V1: We treat nodes as immutable identity. The Observation links to the hash.
        # But we need to link content -> obs.
        # We will Append a "Node Update" or relying on T02 to stitch it?
        # The T02 logic reads TE_Content_Nodes. So we must ensure the node exists.
        
        # If exists, we don't need to re-create.
        Write-Host "[STRATEGY:T01] Dedup: Content exists as $contentId" -ForegroundColor Gray
    }
    else {
        # Create New Node
        $contentId = "CNT-" + (Get-Date).ToString("yyyyMMdd-") + (New-Guid).Guid.SubString(0, 8)
        $nodeEntry = [ordered]@{
            content_id = $contentId
            hash       = $contentHash
            first_seen = $now
            # parents/children added by T02
        }
        if (-not (Test-Path (Split-Path $NodesLog))) { New-Item -ItemType Directory -Path (Split-Path $NodesLog) -Force | Out-Null }
        $nodeEntry | ConvertTo-Json -Compress | Add-Content $NodesLog -Encoding UTF8
        Write-Host "[STRATEGY:T01] Minted New Node: $contentId" -ForegroundColor Cyan
    }

    return [PSCustomObject]@{
        obs_id     = $obsId
        content_id = $contentId
    }
}
catch {
    Write-Error "[STRATEGY:T01] Failed: $_"
    return [PSCustomObject]@{ error = $_.ToString() }
}

