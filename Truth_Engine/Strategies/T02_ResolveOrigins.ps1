<# T02 Origin Resolution #>
param([string]$RootPath = "D:\Infinite\Infinity\Truth_Engine")

$NodesPath = Join-Path $RootPath "Content\TE_Content_Nodes.jsonl"
$EdgePath = Join-Path $RootPath "Content\TE_Origin_Map.jsonl"
$ObsPath = Join-Path $RootPath "Observation\TE_Observations_Log.jsonl"

function Get-Similarity {
    param([string]$a, [string]$b)
    if ([string]::IsNullOrWhiteSpace($a) -or [string]::IsNullOrWhiteSpace($b)) { return 0 }
    $cleanA = $a.ToLower() -replace '[^a-z0-9 ]', ''
    $cleanB = $b.ToLower() -replace '[^a-z0-9 ]', ''
    $tokensA = @($cleanA.Split(" `t`n`r", [System.StringSplitOptions]::RemoveEmptyEntries) | Select-Object -Unique)
    $tokensB = @($cleanB.Split(" `t`n`r", [System.StringSplitOptions]::RemoveEmptyEntries) | Select-Object -Unique)
    $intersection = $tokensA | Where-Object { $tokensB -contains $_ }
    $union = ($tokensA + $tokensB) | Select-Object -Unique
    if ($union.Count -eq 0) { return 0 }
    return [math]::Round($intersection.Count / $union.Count, 2)
}

function Is-ContextualGrowth {
    param([string]$parentText, [string]$childText)
    if ([string]::IsNullOrWhiteSpace($parentText) -or [string]::IsNullOrWhiteSpace($childText)) { return $false }
    $cleanP = $parentText.ToLower() -replace '[^a-z0-9 ]', ''
    $cleanC = $childText.ToLower() -replace '[^a-z0-9 ]', ''
    $tokensP = @($cleanP.Split(" `t`n`r", [System.StringSplitOptions]::RemoveEmptyEntries) | Select-Object -Unique)
    $tokensC = @($cleanC.Split(" `t`n`r", [System.StringSplitOptions]::RemoveEmptyEntries) | Select-Object -Unique)
    $isSubset = $true
    foreach ($t in $tokensP) { if ($tokensC -notcontains $t) { $isSubset = $false; break } }
    return $isSubset
}

if (-not (Test-Path $NodesPath)) { return }
$nodes = @(Get-Content $NodesPath -Encoding UTF8 | ForEach-Object { if ($_) { $_ | ConvertFrom-Json } } | Where-Object { $null -ne $_ })
if ($nodes.Count -eq 0) { return }

$allObs = if (Test-Path $ObsPath) { @(Get-Content $ObsPath -Encoding UTF8 | ForEach-Object { if ($_) { $_ | ConvertFrom-Json } } | Where-Object { $null -ne $_ }) } else { @() }

$cache = @{}
foreach ($node in $nodes) {
    if (@($node.observation_ids).Count -gt 0) {
        $matchedObs = $allObs | Where-Object { $_.obs_id -eq $node.observation_ids[0] } | Select-Object -First 1
        if ($matchedObs) { $cache[$node.content_id] = [PSCustomObject]@{ text = $matchedObs.content; url = $matchedObs.location } }
    }
}

$updated = $false
foreach ($child in $nodes) {
    if (@($child.parents).Count -gt 0) { continue }
    $childData = $cache[$child.content_id]
    if ($null -eq $childData) { continue }

    $bestParent = $null; $bestScore = 0; $method = "original"
    
    # 1. Exact Hash Check (Fastest)
    # 2. Contextual Growth (Quote/Reply)
    # 3. Fuzzy Similarity (Derivative)

    foreach ($parent in $nodes) {
        if ($parent.content_id -eq $child.content_id) { continue }
        try { if ([DateTime]$parent.created_at -ge [DateTime]$child.created_at) { continue } } catch { continue }

        $pData = $cache[$parent.content_id]
        if ($null -eq $pData) { continue }

        # Exact Match (Echo)
        if ($pData.text -eq $childData.text) {
            $bestScore = 1.0; $bestParent = $parent; $method = "exact_echo"; break 
        }

        # Contextual Growth (Subset)
        if (Is-ContextualGrowth -parentText $pData.text -childText $childData.text) { 
            if ($bestScore -lt 1.0) { $bestScore = 1.0; $bestParent = $parent; $method = "contextual_growth" }
        }
        
        # Fuzzy Similarity
        $sim = Get-Similarity -a $childData.text -b $pData.text
        if ($sim -ge 0.80 -and $sim -gt $bestScore) { $bestScore = $sim; $bestParent = $parent; $method = "derivative_echo" }
    }

    if ($bestParent) {
        $child.parents = @($bestParent.content_id); $child.origin_score = $bestScore; $child.origin_method = $method
        $edge = [PSCustomObject]@{ edge_id = "ORIGIN-" + (New-Guid).Guid.SubString(0, 8); parent_id = $bestParent.content_id; child_id = $child.content_id; created_at = (Get-Date).ToUniversalTime().ToString("o"); origin_method = $method; origin_score = $bestScore }
        $null = New-Item -ItemType Directory -Path (Split-Path $EdgePath) -Force -ErrorAction SilentlyContinue
        $edge | ConvertTo-Json -Compress | Add-Content $EdgePath -Encoding UTF8
        Write-Host "[TRUTH:T02] Linked $($child.content_id) -> $($bestParent.content_id) ($method)" -F Cyan
        $updated = $true
    }
}

if ($updated) {
    Remove-Item $NodesPath -Force -ErrorAction SilentlyContinue
    foreach ($n in $nodes) { $n | ConvertTo-Json -Compress | Add-Content $NodesPath -Encoding UTF8 }
}
