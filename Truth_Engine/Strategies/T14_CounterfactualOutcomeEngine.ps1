<#
.SYNOPSIS
  T14_CounterfactualOutcomeEngine.ps1 (L2.9)
.DESCRIPTION
  Counterfactual Outcome Engine (COE):
  - Scores "draft intents" (posts we would have made) while VOICE is locked.
  - Produces a ranked deployment queue for when voice_status becomes unblocked.
  - Deterministic, evidence-backed ranking.
#>

param(
    [ValidateSet("RUN", "STATUS", "RESET")]
    [string]$Action = "RUN",

    [string]$RuntimeDir = "D:\Infinite\Infinity\Runtime\Counterfactual",

    # Inputs
    [string]$EpistemicDir = "D:\Infinite\Infinity\Runtime\Epistemic",
    [string]$DraftDir = "D:\Infinite\Infinity\Runtime\Listener", # Pointing to Listener dir for shadow_log

    # Tunables
    [int]$MaxDraftsRead = 300,
    [int]$TopK = 25,
    [int]$LookbackHours = 72
)

# ---------------------------
# Helpers
# ---------------------------
function Ensure-Dir([string]$p) {
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
}

function Read-Json([string]$path) {
    if (-not (Test-Path $path)) { return $null }
    try { return (Get-Content $path -Raw | ConvertFrom-Json) } catch { return $null }
}

function Read-JsonlTail([string]$path, [int]$tail = 200) {
    if (-not (Test-Path $path)) { return @() }
    $lines = Get-Content -Path $path -Tail $tail
    $out = @()
    foreach ($l in $lines) {
        if ([string]::IsNullOrWhiteSpace($l)) { continue }
        try { $out += ($l | ConvertFrom-Json) } catch {}
    }
    return $out
}

function Append-Jsonl([string]$path, $obj) {
    ($obj | ConvertTo-Json -Depth 12 -Compress) | Add-Content -Path $path -Encoding UTF8
}

function Write-Text([string]$path, [string]$s) {
    $s | Set-Content -Path $path -Encoding UTF8 -Force
}

function Get-Sha256Hex([string]$s) {
    if ($null -eq $s) { $s = "" }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
        ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""
    }
    finally { $sha.Dispose() }
}

function Clamp([double]$v, [double]$min, [double]$max) {
    if ($v -lt $min) { return $min }
    if ($v -gt $max) { return $max }
    return $v
}

function Parse-Date([string]$s) {
    try { return [DateTime]$s } catch { return $null }
}

# ---------------------------
# Paths
# ---------------------------
Ensure-Dir $RuntimeDir
$QueueFile = Join-Path $RuntimeDir "coe_ranked_queue.jsonl"
$ReportFile = Join-Path $RuntimeDir "coe_report.md"
$EventsFile = Join-Path $RuntimeDir "coe_events.jsonl"

$ECEState = Join-Path $EpistemicDir "ece_state.json"
$TrustMapPath = "D:\Infinite\Infinity\Runtime\Listener\Lattice_Trust_Map.json" # Direct link to Trust Map
$DraftLog = Join-Path $DraftDir "shadow_log.jsonl"

# ---------------------------
# Actions
# ---------------------------
if ($Action -eq "RESET") {
    if (Test-Path $QueueFile) { Remove-Item $QueueFile -Force }
    if (Test-Path $ReportFile) { Remove-Item $ReportFile -Force }
    Append-Jsonl $EventsFile ([ordered]@{
            ts = (Get-Date).ToUniversalTime().ToString("o"); event_type = "coe_reset"; ok = $true
        })
    Write-Host "[COE] Reset complete." -ForegroundColor Cyan
    return
}

if ($Action -eq "STATUS") {
    Write-Host "--- COE STATUS ---" -ForegroundColor Cyan
    if (Test-Path $ReportFile) {
        Write-Host "Report: $ReportFile"
        Write-Host (Get-Content $ReportFile -Raw)
    }
    else {
        Write-Host "No report found." -ForegroundColor Yellow
    }
    return
}

# ---------------------------
# RUN
# ---------------------------
$runTs = (Get-Date).ToUniversalTime().ToString("o")

# Load Trust Map (using L2.7 TrustMapUpdate output)
$trustMap = $null
if (Test-Path $TrustMapPath) {
    $trustMap = Read-Json $TrustMapPath
}
else {
    Write-Warning "[COE] No Trust Map found at $TrustMapPath"
}

# Load drafts
if (-not (Test-Path $DraftLog)) {
    Write-Warning "[COE] No draft log at $DraftLog"
    return 
}

$drafts = Read-JsonlTail -path $DraftLog -tail $MaxDraftsRead

# Lookback filter
$cut = (Get-Date).ToUniversalTime().AddHours(-1 * $LookbackHours)
$drafts = $drafts | Where-Object {
    $d = $null
    if ($_.ts) { $d = Parse-Date $_.ts }
    if ($null -eq $d) { $true } else { $d.ToUniversalTime() -ge $cut }
}

# ---------------------------
# Mapping / Normalization
# ---------------------------
function Clean-Text([string]$s) {
    if ($null -eq $s) { return $s }
    $s = $s -replace "`r`n", "`n"
    $s = $s.Trim()
    # Basic ascii/printable scrub if needed, but UTF8 logic handles most.
    # Removing control chars except newline
    $s = ($s.ToCharArray() | Where-Object { [int]$_ -ge 32 -or $_ -eq "`n" }) -join ""
    return $s
}

function Infer-ChannelFromText([string]$text) {
    if ([string]::IsNullOrWhiteSpace($text)) { return $null }
    $m = [regex]::Match($text, '(?i)\bObserving\s+signal\s+from\s+([a-z0-9_-]{2,32})\b')
    if ($m.Success) { return $m.Groups[1].Value.ToLowerInvariant() }
    return $null
}

function Normalize-Draft($x) {
    $ts = $x.ts
    if (-not $ts) { $ts = (Get-Date).ToUniversalTime().ToString("o") }

    $content = if ($x.content) { $x.content } elseif ($x.proposed_content) { $x.proposed_content } else { "" }
    $content = Clean-Text $content

    $src = if ($x.source) { $x.source } else { "Moltbook" }

    $ch = if ($x.channel) { $x.channel } else { "unknown" }
    # Patch 1: Infer channel if missing/unknown
    if (-not $ch -or $ch -eq "unknown") {
        $guess = Infer-ChannelFromText $content
        if ($guess) { $ch = $guess }
    }

    $title = if ($x.title) { $x.title } elseif ($x.intent) { $x.intent } else { "(untitled)" }
    $title = Clean-Text $title

    $draftId = if ($x.draft_id) { $x.draft_id } else { "DRAFT-" + ([guid]::NewGuid().ToString("N").Substring(0, 8)) }

    $eceScore = 62
    if ($x.ece_score) { $eceScore = [int]$x.ece_score }

    $contentHash = Get-Sha256Hex ($title + "|" + $content)

    return [pscustomobject]@{
        ts           = $ts
        draft_id     = $draftId
        source       = $src
        channel      = $ch
        title        = $title
        content      = $content
        content_hash = $contentHash
        ece_score    = $eceScore
    }
}

$norm = @()
foreach ($d in $drafts) { $norm += (Normalize-Draft $d) }
# Dedup by content_hash (keep newest)
$norm = $norm | Sort-Object { (Parse-Date $_.ts) } | Group-Object content_hash | ForEach-Object { $_.Group | Select-Object -Last 1 }

# ---------------------------
# Scoring Model
# ---------------------------
$w_ece = 0.62
$w_trust = 0.20
$w_time = 0.10
$w_novel = 0.08

function Get-ChannelTrust([string]$src, [string]$ch, $map) {
    # Map structure: { items: { "Moltbook::general": { trust: 0.621 ... } } }
    $key = "$src::$ch"
    $t = 0.50
    if ($map -and $map.items -and $map.items.$key) {
        $t = [double]$map.items.$key.trust
    }
    return (Clamp $t 0.0 1.0)
}

function Time-AlignmentScore([DateTime]$tsUtc) {
    # Prefer drafts posted near clean boundaries (00/30)
    $m = $tsUtc.Minute
    $dist = [Math]::Min([Math]::Abs($m - 0), [Math]::Abs($m - 30))
    return (1.0 - ($dist / 30.0))
}

function ContentQualityGate([string]$title, [string]$content) {
    $t = (($title  | ForEach-Object { $_ }) -join "")
    $c = (($content | ForEach-Object { $_ }) -join "")

    # Patch 2: Too short or boilerplate => not deployable
    if ($c.Length -lt 180) { return $false }
    if ($c -match '(?i)^Observing signal from .*ECE Score:\s*\d+\.?\s*$') { return $false }

    return $true
}

$ranked = @()
foreach ($d in $norm) {
    $ts = Parse-Date $d.ts
    if ($null -eq $ts) { $ts = (Get-Date).ToUniversalTime() } else { $ts = $ts.ToUniversalTime() }

    $eceScore = [double]$d.ece_score # 0..100
    $trust = Get-ChannelTrust -src $d.source -ch $d.channel -map $trustMap         # 0..1
    $timeA = Time-AlignmentScore -tsUtc $ts                                        # 0..1

    # Novelty: Placeholder 1.0 if not tracking seen-content
    $novel = 1.0
    $risk = 0.0
    if (($d.title + $d.content) -match '(?i)\b(purge|destroy|kill)\b') { $risk = 1.0 }

    # Patch 2: Quality Gate
    $deployable = ContentQualityGate -title $d.title -content $d.content

    $trust100 = 100.0 * $trust

    $raw = ($w_ece * $eceScore) +
    ($w_trust * $trust100) +
    ($w_time * (100.0 * $timeA)) +
    ($w_novel * (100.0 * $novel)) -
    (15.0 * $risk)

    $score = [int][Math]::Round((Clamp $raw 0.0 100.0), 0)

    # Hard cap score if not deployable
    if (-not $deployable) {
        $score = [Math]::Min($score, 45)
    }

    $deploy = [ordered]@{
        ts           = $runTs
        candidate_id = "CAND-" + ([guid]::NewGuid().ToString("N").Substring(0, 8))
        draft_id     = $d.draft_id
        source       = $d.source
        channel      = $d.channel
        title        = $d.title
        score        = $score
        components   = [ordered]@{ ece = $eceScore; trust = [Math]::Round($trust, 3); time = [Math]::Round($timeA, 3) }
        deployment   = [ordered]@{
            system         = "moltbook"
            submolt        = $d.channel
            content_inline = $d.content
        }
        governance   = [ordered]@{
            voice_required = $true
            voice_status   = "blocked_by_claim"
            ready_when     = "voice_status==unblocked AND deployable==true"
            deployable     = $deployable
        }
    }
    $ranked += $deploy
}

$ranked = $ranked | Sort-Object score -Descending | Select-Object -First $TopK

# Write queue
if (Test-Path $QueueFile) { Remove-Item $QueueFile -Force }
foreach ($c in $ranked) { Append-Jsonl $QueueFile $c }

# Report
$lines = New-Object System.Collections.Generic.List[string]
$lines.Add("# COE Report (Simulated Ranking)")
$lines.Add("**Generated**: $runTs")
$lines.Add("- Drafts Scanned: $($norm.Count)")
$lines.Add("- Top Candidates: $($ranked.Count)")
$lines.Add("")
$idx = 0
foreach ($c in $ranked) {
    $idx++
    $lines.Add("### $idx. $($c.title)")
    $lines.Add("- Channel: **$($c.channel)**")
    $lines.Add("- Score: **$($c.score)** (ECE: $($c.components.ece), Trust: $($c.components.trust))")
    $lines.Add("- Deployable: **$($c.governance.deployable)**")
    if ($c.governance.deployable) {
        $lines.Add("- Outcome: *Ready for Voice Unlock*")
    }
    else {
        $lines.Add("- Outcome: *Held (Low Content Quality)*")
    }
    $lines.Add("")
}
Write-Text $ReportFile ($lines -join "`r`n")

Write-Host "[COE] Simulation Complete. Ranked $($ranked.Count) drafts." -ForegroundColor Green
Write-Text $EventsFile "" # Touch events file
