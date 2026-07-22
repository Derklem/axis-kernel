<# T04 Claim Aggregation #>
param([string]$RootPath = "D:\Infinite\Infinity\Truth_Engine")

$NodesPath = Join-Path $RootPath "Content\TE_Content_Nodes.jsonl"
$ObsPath = Join-Path $RootPath "Observation\TE_Observations_Log.jsonl"
$ProfilePath = Join-Path $RootPath "Content\TE_Source_Profiles.jsonl"
$ClaimsPath = Join-Path $RootPath "Content\TE_Claims_Index.jsonl"

if (-not (Test-Path $NodesPath) -or -not (Test-Path $ObsPath)) { return }

# 1. Load Data
$nodes = @(Get-Content $NodesPath -Encoding UTF8 | ForEach-Object { if ($_) { $_ | ConvertFrom-Json } } | Where-Object { $null -ne $_ })
if ($nodes.Count -eq 0) { return }

$allObs = @(Get-Content $ObsPath -Encoding UTF8 | ForEach-Object { if ($_) { $_ | ConvertFrom-Json } } | Where-Object { $null -ne $_ })
$profiles = @(if (Test-Path $ProfilePath) { Get-Content $ProfilePath -Encoding UTF8 | ForEach-Object { if ($_) { $_ | ConvertFrom-Json } } | Where-Object { $null -ne $_ } } else { @() })

$bucketMap = @{}
foreach ($p in $profiles) { $bucketMap[$p.source_id] = $p.bucket }

function Get-ClaimSignature {
    param([string]$text)
    if ([string]::IsNullOrWhiteSpace($text)) { return "empty" }
    $clean = $text.ToLower() -replace '[^a-z0-9 ]', ''
    $tokens = @($clean.Split(" `t`n`r", [System.StringSplitOptions]::RemoveEmptyEntries) | Select-Object -Unique | Sort-Object)
    return ($tokens -join " ")
}

# 2. Cluster Content Nodes
$claimClusters = @{}
foreach ($node in $nodes) {
    if (@($node.observation_ids).Count -gt 0) {
        $firstObsId = $node.observation_ids[0]
        $matchedObs = $allObs | Where-Object { $_.obs_id -eq $firstObsId } | Select-Object -First 1
        if ($matchedObs) {
            $sig = Get-ClaimSignature -text $matchedObs.content
            if (-not $claimClusters.ContainsKey($sig)) { $claimClusters[$sig] = New-Object System.Collections.Generic.List[PSCustomObject] }
            $claimClusters[$sig].Add($node)
        }
    }
}

# 3. Form Claim Nodes
$claims = New-Object System.Collections.Generic.List[PSCustomObject]
$existingClaims = @(if (Test-Path $ClaimsPath) { Get-Content $ClaimsPath -Encoding UTF8 | ForEach-Object { if ($_) { $_ | ConvertFrom-Json } } | Where-Object { $null -ne $_ } } else { @() })

foreach ($sig in $claimClusters.Keys) {
    $clusterNodes = @($claimClusters[$sig])
    $bestText = ""; $maxLen = -1
    foreach ($cn in $clusterNodes) {
        if (@($cn.observation_ids).Count -gt 0) {
            $matchedObs = $allObs | Where-Object { $_.obs_id -eq $cn.observation_ids[0] } | Select-Object -First 1
            if ($matchedObs -and $matchedObs.content.Length -gt $maxLen) { $maxLen = $matchedObs.content.Length; $bestText = $matchedObs.content }
        }
    }

    $support = [PSCustomObject]@{ PRIMARY = 0; GROWTH = 0; IGNORE = 0 }
    $contentIds = New-Object System.Collections.Generic.List[string]
    
    foreach ($cn in $clusterNodes) {
        $contentIds.Add($cn.content_id)
        foreach ($obsId in @($cn.observation_ids)) {
            $o = $allObs | Where-Object { $_.obs_id -eq $obsId } | Select-Object -First 1
            if ($o) {
                $bucket = $bucketMap[$o.source_id]
                if ($null -eq $bucket) { $bucket = "IGNORE" }
                if ($bucket -eq "PRIMARY") { $support.PRIMARY++ }
                elseif ($bucket -eq "GROWTH") { $support.GROWTH++ }
                else { $support.IGNORE++ }
            }
        }
    }

    $claim = $existingClaims | Where-Object { (Get-ClaimSignature -text $_.canonical_text) -eq $sig } | Select-Object -First 1
    if ($null -eq $claim) {
        $claim = [PSCustomObject]@{
            claim_id = "CLM-" + (Get-Date).ToUniversalTime().ToString("yyyyMMdd-") + (New-Guid).Guid.SubString(0, 8)
            created_at = (Get-Date).ToUniversalTime().ToString("o"); updated_at = (Get-Date).ToUniversalTime().ToString("o")
            canonical_text = $bestText; content_ids = $contentIds.ToArray(); support = $support
            oppose = [PSCustomObject]@{ PRIMARY = 0; GROWTH = 0; IGNORE = 0 }; cluster_method = "token_set_v1"; cluster_score = 1.0
        }
    }
    else {
        $claim.updated_at = (Get-Date).ToUniversalTime().ToString("o")
        $claim.content_ids = @(($contentIds.ToArray() + @($claim.content_ids)) | Select-Object -Unique)
        $claim.support = $support; $claim.canonical_text = $bestText
    }
    $claims.Add($claim)
    Write-Host "[TRUTH:T04] Claim $($claim.claim_id) (P=$($support.PRIMARY) G=$($support.GROWTH) I=$($support.IGNORE))" -ForegroundColor Cyan
}

if ($claims.Count -gt 0) {
    $tempPath = "$ClaimsPath.tmp"
    $claims | ForEach-Object { $_ | ConvertTo-Json -Compress -Depth 10 } | Set-Content $tempPath -Encoding UTF8
    Move-Item $tempPath $ClaimsPath -Force
}
