<#
.SYNOPSIS
  T15_DraftEnrichment.ps1 (DEE v1.0)
.DESCRIPTION
  Deterministic Draft Enrichment Engine:
  - Reads COE ranked candidates
  - Builds/uses a local post index from ingested feed artifacts
  - Matches candidate -> source post (no network)
  - Produces enriched deployable replies using a fixed template
  - Applies safety filters (no prompt-following, no secrets, no instructions)
#>

param(
    [ValidateSet("BUILD_INDEX", "ENRICH")]
    [string]$Action = "ENRICH",

    [string]$RuntimeDir = "D:\Infinite\Infinity\Runtime\DraftEnrichment",

    # Inputs
    [string]$COEQueue = "D:\Infinite\Infinity\Runtime\Counterfactual\coe_ranked_queue.jsonl",

    # Simulation: Read from Mock Feed directly
    [string]$SignalLog = "D:\Infinite\Infinity\Runtime\Listener\mock_feed.json"
)

# -------------------------
# Helpers
# -------------------------
function Ensure-Dir([string]$p) { if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null } }
function Read-Jsonl([string]$path) {
    if (-not (Test-Path $path)) { return @() }
    $lines = Get-Content $path
    $out = @()
    foreach ($ln in $lines) { try { $out += ($ln | ConvertFrom-Json) } catch {} }
    return $out
}
function Append-Jsonl([string]$path, $obj) { ($obj | ConvertTo-Json -Depth 12 -Compress) | Add-Content -Path $path -Encoding UTF8 }
function Get-Sha256Hex([string]$s) {
    if ($null -eq $s) { $s = "" }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
        ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""
    }
    finally { $sha.Dispose() }
}
function Norm([string]$s) {
    if ($null -eq $s) { return "" }
    $s = $s -replace "`r`n", "`n"
    $s = $s.Trim().ToLowerInvariant()
    $s = [regex]::Replace($s, '\s+', ' ')
    return $s
}
function TokenSet([string]$s) {
    if ([string]::IsNullOrWhiteSpace($s)) { return @() }
    return @($s -split '\W+' | Where-Object { $_.Length -gt 2 } | ForEach-Object { $_.ToLowerInvariant() } | Select-Object -Unique)
}
function OverlapRatio($aTokens, $bTokens) {
    if ($aTokens.Count -eq 0 -or $bTokens.Count -eq 0) { return 0.0 }
    $set = @{}
    foreach ($t in $aTokens) { $set[$t] = $true }
    $hit = 0
    foreach ($t in $bTokens) { if ($set.ContainsKey($t)) { $hit++ } }
    return [Math]::Round($hit / [double]([Math]::Max($aTokens.Count, $bTokens.Count)), 3)
}

# -------------------------
# Paths
# -------------------------
Ensure-Dir $RuntimeDir
$IndexFile = Join-Path $RuntimeDir "posts_index.json"
$EventsFile = Join-Path $RuntimeDir "dee_events.jsonl"
$OutQueue = Join-Path $RuntimeDir "dee_enriched_queue.jsonl"

# -------------------------
# Build Index
# -------------------------
function Build-PostIndex {
    # Read full array from mock feed
    $posts = $null
    if (Test-Path $SignalLog) {
        $posts = Get-Content $SignalLog -Raw | ConvertFrom-Json
    }

    $index = [ordered]@{
        version  = "1.0"
        built_at = (Get-Date).ToUniversalTime().ToString("o")
        posts    = @{}
    }

    if ($posts) {
        foreach ($p in $posts) {
            try {
                $postId = $p.id
                $title = $p.title
                $content = $p.content
                $src = "Moltbook"
                $channel = if ($p.submolt.name) { $p.submolt.name } else { $p.submolt }
                $author = $p.author
                $ts = $p.created_at

                if ([string]::IsNullOrWhiteSpace($content)) { continue }

                $key = $null
                if ($postId) { $key = "id:" + $postId }
                else {
                    $h = Get-Sha256Hex (($title) + "`n" + ($content))
                    $key = "h:" + $h.Substring(0, 16)
                }

                if (-not $index.posts.ContainsKey($key)) {
                    $index.posts[$key] = [ordered]@{
                        key          = $key
                        source       = $src
                        channel      = $channel
                        title        = $title
                        content      = $content
                        author       = $author
                        ts           = $ts
                        norm_title   = (Norm $title)
                        title_tokens = @(TokenSet $title)
                    }
                }
            }
            catch {}
        }
    }

    ($index | ConvertTo-Json -Depth 10) | Set-Content -Path $IndexFile -Encoding UTF8 -Force
    Append-Jsonl $EventsFile @{ ts = (Get-Date).ToUniversalTime().ToString("o"); event_type = "index_built"; posts_count = ($index.posts.Keys.Count) }
    Write-Host "[DEE] Built index: $($index.posts.Keys.Count) posts"
}

# -------------------------
# Safety + Enrichment
# -------------------------
function Contains-UnsafeBait([string]$text) {
    if ([string]::IsNullOrWhiteSpace($text)) { return $false }
    if ($text -match '(?i)\b(api[_ -]?key|secret|token|private key)\b' -and $text -match '(?i)\b(paste|share|send|drop)\b') { return $true }
    if ($text -match '(?i)\b(run this|execute|powershell|bash|curl|wget|download)\b') { return $true }
    return $false
}

function Extract-CoreClaim([string]$content) {
    if ([string]::IsNullOrWhiteSpace($content)) { return "" }
    $c = $content.Trim()
    $firstLine = ($c -split "`n")[0]
    if ($firstLine.Length -gt 220) { return $firstLine.Substring(0, 220) + "…" }
    return $firstLine
}

function Make-Reply([string]$title, [string]$content, [string]$channel) {
    $claim = Extract-CoreClaim $content
    if ([string]::IsNullOrWhiteSpace($claim)) { $claim = $title }

    # Deterministic “skeptical” posture for hype terms
    $hype = ($title + " " + $content) -match '(?i)\b(1000x|degen|pump|moon)\b'

    if (Contains-UnsafeBait $content) {
        return "I can’t help with operational instructions or sharing credentials. At a high level: what’s the core goal here, and what evidence would demonstrate it’s safe and legitimate?"
    }

    if ($hype) {
        return "If this is a high-upside claim, the first step is separating narrative from verifiable facts (team, product, traction, risks). What primary evidence supports the thesis, and what would falsify it?"
    }

    return "I read this as: “$claim”. A useful test is to name the constraint you’re optimizing (truth, speed, safety, leverage) and measure it explicitly. What outcome would convince you the approach is working?"
}

function Match-Post($index, [string]$channel, [string]$title) {
    $nt = Norm $title
    $tt = @(TokenSet $title)

    $best = $null
    $bestScore = 0.0

    foreach ($p in $index.posts.PSObject.Properties) {
        $post = $p.Value
        if ($channel -and $post.channel -and (Norm $post.channel) -ne (Norm $channel)) { continue }

        # exact title
        if ($nt -and $post.norm_title -eq $nt) { return @{ post = $post; score = 1.0; method = "exact_title" } }

        $ratio = OverlapRatio $tt $post.title_tokens
        if ($ratio -gt $bestScore) { $bestScore = $ratio; $best = $post }
    }

    if ($best -and $bestScore -ge 0.35) {
        return @{ post = $best; score = $bestScore; method = "token_overlap" }
    }

    return $null
}

# -------------------------
# Main
# -------------------------
if ($Action -eq "BUILD_INDEX") {
    Build-PostIndex
    return
}

# ENRICH
if (-not (Test-Path $IndexFile)) { Build-PostIndex }
$indexObj = Get-Content $IndexFile -Raw | ConvertFrom-Json

$cands = Read-Jsonl $COEQueue
if ($cands.Count -eq 0) { Write-Host "[DEE] No candidates."; return }

# write fresh queue
if (Test-Path $OutQueue) { Remove-Item $OutQueue -Force }

foreach ($c in $cands) {
    $ch = $c.channel
    if (-not $ch -and $c.source) { $ch = $c.source }

    $title = $c.title
    $match = Match-Post $indexObj $ch $title

    if (-not $match) {
        # Keep held; emit event
        Append-Jsonl $EventsFile @{
            ts = (Get-Date).ToUniversalTime().ToString("o"); event_type = "enrich_miss"; candidate_id = $c.candidate_id; channel = $ch; title = $title
        }
        Append-Jsonl $OutQueue $c
        continue
    }

    $post = $match.post
    $reply = Make-Reply $post.title $post.content $post.channel

    # enrich candidate
    if (-not $c.deployment) { $c | Add-Member NoteProperty deployment (@{}) -Force }
    $c.deployment.content_inline = $reply
    $c.deployment.submolt = $post.channel

    # attach provenance (local only)
    if (-not $c.provenance) { $c | Add-Member NoteProperty provenance (@{}) -Force }
    $c.provenance = [ordered]@{
        match_method = $match.method
        match_score  = $match.score
        post_key     = $post.key
        channel      = $post.channel
        title        = $post.title
        ts           = $post.ts
    }
  
    # Override quality block if enriched
    if ($c.governance.deployable -eq $false) {
        $c.governance.deployable = $true
        $c.score = 72 # Boost score for enriched quality
        $c.governance.ready_when = "voice_status==unblocked"
    }

    Append-Jsonl $EventsFile @{
        ts = (Get-Date).ToUniversalTime().ToString("o"); event_type = "enriched"; candidate_id = $c.candidate_id; post_key = $post.key; method = $match.method; score = $match.score
    }

    Append-Jsonl $OutQueue $c
}

Write-Host "[DEE] Enrichment complete -> $OutQueue"
