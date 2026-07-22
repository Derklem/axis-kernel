<# T03 Source Bucketing #>
param([string]$RootPath = "D:\Infinite\Infinity\Truth_Engine")

$NodesPath = Join-Path $RootPath "Content\TE_Content_Nodes.jsonl"
$ObsPath = Join-Path $RootPath "Observation\TE_Observations_Log.jsonl"
$ProfilePath = Join-Path $RootPath "Content\TE_Source_Profiles.jsonl"

if (-not (Test-Path $NodesPath) -or -not (Test-Path $ObsPath)) { return }

# 1. Load Data
$nodes = @(Get-Content $NodesPath -Encoding UTF8 | ForEach-Object { if ($_) { $_ | ConvertFrom-Json } } | Where-Object { $null -ne $_ })
$allObs = @(Get-Content $ObsPath -Encoding UTF8 | ForEach-Object { if ($_) { $_ | ConvertFrom-Json } } | Where-Object { $null -ne $_ })

if ($nodes.Count -eq 0 -or $allObs.Count -eq 0) { return }

# 2. Map Nodes to Original Sources
$nodeOwnerMap = @{}
foreach ($node in $nodes) {
    if (@($node.observation_ids).Count -gt 0) {
        $firstObsId = $node.observation_ids[0]
        $matchedObs = $allObs | Where-Object { $_.obs_id -eq $firstObsId } | Select-Object -First 1
        if ($matchedObs) { $nodeOwnerMap[$node.content_id] = $matchedObs.source_id }
    }
}

# 3. Assess Each Source
$sourceIds = @($allObs | Select-Object -ExpandProperty source_id -Unique)
$profiles = New-Object System.Collections.Generic.List[PSCustomObject]

foreach ($sid in $sourceIds) {
    if ([string]::IsNullOrWhiteSpace($sid)) { continue }
    $sObs = @($allObs | Where-Object { $_.source_id -eq $sid })
    if ($sObs.Count -eq 0) { continue }
    $sContentIds = New-Object System.Collections.Generic.HashSet[string]
    foreach ($o in $sObs) {
        $matchedNode = $nodes | Where-Object { $o.obs_id -in @($_.observation_ids) } | Select-Object -First 1
        if ($matchedNode) { [void]$sContentIds.Add($matchedNode.content_id) }
    }
    $totalUnique = $sContentIds.Count
    if ($totalUnique -eq 0) { continue }
    
    $originalCount = 0; $remixCount = 0; $repostCount = 0; $depthSum = 0
    foreach ($cid in $sContentIds) {
        $node = $nodes | Where-Object { $_.content_id -eq $cid } | Select-Object -First 1
        $isOwner = ($nodeOwnerMap[$cid] -eq $sid); $hasParents = (@($node.parents).Count -gt 0)
        if ($isOwner) { if (-not $hasParents) { $originalCount++ } else { $remixCount++ }; $depthSum += if ($hasParents) { 1 } else { 0 } }
        else { $repostCount++; $depthSum += 2 }
    }
    
    $origFreq = [math]::Round([double]$originalCount / $totalUnique, 2)
    $remixRatio = [math]::Round([double]$remixCount / $totalUnique, 2)
    $repostRatio = [math]::Round([double]$repostCount / $totalUnique, 2)
    $avgDepth = [math]::Round([double]$depthSum / $totalUnique, 2)
    
    $bucket = "IGNORE"; $score = 0.5
    if ($origFreq -ge 0.40 -and $repostRatio -le 0.40) { $bucket = "PRIMARY"; $score = $origFreq }
    elseif ($remixRatio -ge 0.25 -or ($origFreq -gt 0.05 -and $repostRatio -lt 0.70)) { $bucket = "GROWTH"; $score = $remixRatio }
    else { $bucket = "IGNORE"; $score = $repostRatio }
    
    $profiles.Add([PSCustomObject]@{
            source_id = $sid; first_seen_at = @($sObs | Sort-Object seen_at)[0].seen_at; last_seen_at = @($sObs | Sort-Object seen_at -Descending)[0].seen_at
            observations = $sObs.Count; unique_content = $totalUnique; origination_frequency = $origFreq; remix_ratio = $remixRatio; repost_ratio = $repostRatio; avg_origin_depth = $avgDepth
            bucket = $bucket; bucket_score = $score; bucket_method = "heuristic_v3.1"
        })
}

if ($profiles.Count -gt 0) {
    Remove-Item $ProfilePath -Force -ErrorAction SilentlyContinue
    foreach ($p in $profiles) { $p | ConvertTo-Json -Compress | Add-Content $ProfilePath -Encoding UTF8 }
}
