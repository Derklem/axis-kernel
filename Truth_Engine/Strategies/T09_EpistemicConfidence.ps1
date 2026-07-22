<#
.SYNOPSIS
  T09_EpistemicConfidence.ps1 (L2.6)
.DESCRIPTION
  Deterministic Epistemic Confidence Engine:
  - Computes confidence vector + score
  - Maintains rolling 24h counts (content hash / author hash)
  - Detects burstiness per channel (5m buckets)
  - Produces verdict: accept|downweight|quarantine
  - Appends evidence-bearing events to ece_events.jsonl
#>

param(
    [ValidateSet("EVALUATE_ONE", "MAINTAIN")]
    [string]$Action = "EVALUATE_ONE",

    # For EVALUATE_ONE, pass JSON via -InputJson or pipeline
    [string]$InputJson,

    # Runtime
    [string]$RuntimeDir = "D:\Infinite\Infinity\Runtime\Epistemic"
)

# ---------------------------
# Helpers
# ---------------------------
function Ensure-Dir([string]$p) {
    if (-not (Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null }
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

function Read-Json([string]$path) {
    if (-not (Test-Path $path)) { return $null }
    try { return (Get-Content $path -Raw | ConvertFrom-Json) } catch { return $null }
}

function Write-Json([string]$path, $obj, [int]$depth = 8) {
    $obj | ConvertTo-Json -Depth $depth | Set-Content -Path $path -Encoding UTF8 -Force
}

function Append-Jsonl([string]$path, $obj) {
    ($obj | ConvertTo-Json -Depth 10 -Compress) | Add-Content -Path $path -Encoding UTF8
}

function Clamp([int]$v, [int]$min, [int]$max) {
    if ($v -lt $min) { return $min }
    if ($v -gt $max) { return $max }
    return $v
}

# ---------------------------
# Paths
# ---------------------------
Ensure-Dir $RuntimeDir
$StateFile = Join-Path $RuntimeDir "ece_state.json"
$EventsFile = Join-Path $RuntimeDir "ece_events.jsonl"
$QuarantineFile = Join-Path $RuntimeDir "ece_quarantine.jsonl"

# ---------------------------
# Load/Init State
# ---------------------------
$state = Read-Json $StateFile
if (-not $state) {
    $state = [ordered]@{
        version    = "1.0"
        updated_at = (Get-Date).ToUniversalTime().ToString("o")
        sources    = @{ Moltbook = @{ trust = 0.65 } }
        channels   = @{}
        hashes     = @{
            content_seen_24h = @{}
            author_seen_24h  = @{}
        }
    }
}

function Prune-24hMaps {
    param([hashtable]$map)
    $cut = (Get-Date).ToUniversalTime().AddHours(-24)
    $keys = @($map.Keys)
    foreach ($k in $keys) {
        try {
            $ls = [DateTime]$map[$k].last_seen
            if ($ls -lt $cut) { $map.Remove($k) }
        }
        catch {
            # if corrupt, remove
            $map.Remove($k)
        }
    }
}

# ---------------------------
# MAINTAIN
# ---------------------------
if ($Action -eq "MAINTAIN") {
    Prune-24hMaps -map $state.hashes.content_seen_24h
    Prune-24hMaps -map $state.hashes.author_seen_24h
    $state.updated_at = (Get-Date).ToUniversalTime().ToString("o")
    Write-Json $StateFile $state 10
    Write-Host "[ECE] Maintenance complete."
    return
}

# ---------------------------
# EVALUATE_ONE
# ---------------------------
if ($Action -ne "EVALUATE_ONE") { throw "Unknown Action" }

# Acquire input
$obs = $null
if ($InputJson) {
    $obs = $InputJson | ConvertFrom-Json
}
else {
    # try pipeline
    $p = @()
    while ($input.MoveNext()) { $p += $input.Current }
    if ($p.Count -gt 0) {
        $obs = ($p -join "`n") | ConvertFrom-Json
    }
    else {
        throw "No input observation provided."
    }
}

# Basic extraction
$src = $obs.source
if (-not $src) { $src = "unknown" }
$ch = $obs.channel
if (-not $ch -and $obs.payload -and $obs.payload.Channel) { $ch = $obs.payload.Channel }
if (-not $ch) { $ch = "unknown" }

$text = ""
if ($obs.payload -and $obs.payload.Content) { $text = [string]$obs.payload.Content }
elseif ($obs.content) { $text = [string]$obs.content }

$author = ""
try {
    if ($obs.payload -and $obs.payload.Metadata -and $obs.payload.Metadata.author) { $author = [string]$obs.payload.Metadata.author }
}
catch {}

$contentHash = Get-Sha256Hex $text
$authorHash = Get-Sha256Hex $author

# Update rolling seen maps
function Touch-Seen([hashtable]$map, [string]$key) {
    $now = (Get-Date).ToUniversalTime().ToString("o")
    if (-not $map.ContainsKey($key)) {
        $map[$key] = @{ count = 1; last_seen = $now }
    }
    else {
        $map[$key].count = [int]$map[$key].count + 1
        $map[$key].last_seen = $now
    }
}

Touch-Seen $state.hashes.content_seen_24h $contentHash
Touch-Seen $state.hashes.author_seen_24h  $authorHash

# Prune
Prune-24hMaps $state.hashes.content_seen_24h
Prune-24hMaps $state.hashes.author_seen_24h

$seenContent = [int]$state.hashes.content_seen_24h[$contentHash].count
$seenAuthor = [int]$state.hashes.author_seen_24h[$authorHash].count

# Compute token entropy (simple proxy)
# Entropy proxy: unique_tokens / total_tokens, bounded
$tokens = @()
if (-not [string]::IsNullOrWhiteSpace($text)) {
    $tokens = ($text -split '\W+' | Where-Object { $_.Length -gt 2 } | ForEach-Object { $_.ToLower() })
}
$total = $tokens.Count
$uniq = @($tokens | Select-Object -Unique).Count
$entropy = 0.0
if ($total -gt 0) {
    $entropy = [Math]::Round(($uniq / [double]$total), 3)
}

# Signals
$tags = @()
try {
    if ($obs.payload -and $obs.payload.Tags) { $tags += $obs.payload.Tags }
}
catch {}
$tags = @($tags | Select-Object -Unique)

# Vector scoring components
$vector = [ordered]@{
    source_trust         = 0
    content_novelty      = 0
    burstiness           = 0
    duplication_pressure = 0
    risk_language        = 0
    schema_integrity     = 0
}

$reasons = New-Object System.Collections.ArrayList

# (A) source_trust (0..25)
$trust = 0.50
try {
    if ($state.sources.ContainsKey($src) -and $state.sources[$src].trust) { $trust = [double]$state.sources[$src].trust }
}
catch {}
$vector.source_trust = [int]([Math]::Round(25 * $trust))

# (B) content_novelty (-15..+15)
# more repeats => penalty; high uniqueness => boost
if ($seenContent -eq 1) { $vector.content_novelty = 12 }
elseif ($seenContent -le 3) { $vector.content_novelty = 0 }
else { $vector.content_novelty = -12; [void]$reasons.Add("repeat_content") }

# (C) duplication_pressure (-20..0)
if ($seenContent -ge 5) { $vector.duplication_pressure = -20; [void]$reasons.Add("dup_pressure") }
elseif ($seenContent -ge 3) { $vector.duplication_pressure = -10 }

# (D) risk_language (-20..0)
if ($tags -contains "HIGH_RISK_LANGUAGE") { $vector.risk_language = -20; [void]$reasons.Add("risk_language_tag") }

# (E) schema_integrity (0 or large negative)
# If required fields absent, punish hard (prevents garbage entering trusted state)
$schemaOk = $true
if (-not $obs.timestamp -and -not $obs.ts) { $schemaOk = $false } # Allow 'ts' as timestamp alias
# if (-not $obs.payload) { $schemaOk = $false } # Payload optional if content is top-level? Spec said payload. 
if ($obs.content) { $schemaOk = $true } # Relax for simple ingest objects if content exists

if (-not $schemaOk) {
    $vector.schema_integrity = -50
    [void]$reasons.Add("schema_missing_fields")
}
else {
    $vector.schema_integrity = 0
}

# (F) burstiness (-25..0)
# Minimal approach: channel baseline (avg_per_5m) and a current bin counter
# Maintain a per-channel 5-minute bucket counter in memory state
$nowUtc = (Get-Date).ToUniversalTime()
$bucket = $nowUtc.ToString("yyyyMMddHH") + "-" + ([int]([Math]::Floor($nowUtc.Minute / 5))).ToString("00")

if (-not $state.channels.ContainsKey($ch)) {
    $state.channels[$ch] = @{ avg_per_5m = 2.0; bins = @{} }
}
if (-not $state.channels[$ch].bins) { $state.channels[$ch].bins = @{} }

if (-not $state.channels[$ch].bins.ContainsKey($bucket)) {
    $state.channels[$ch].bins[$bucket] = @{ count = 1; ts = $nowUtc.ToString("o") }
}
else {
    $state.channels[$ch].bins[$bucket].count = [int]$state.channels[$ch].bins[$bucket].count + 1
}

# prune old bins (keep last 12 bins = 1 hour)
$binKeys = @($state.channels[$ch].bins.Keys | Sort-Object)
if ($binKeys.Count -gt 12) {
    $remove = $binKeys[0..($binKeys.Count - 13)]
    foreach ($rk in $remove) { $state.channels[$ch].bins.Remove($rk) }
}

$currentCount = [int]$state.channels[$ch].bins[$bucket].count
$avg = [double]$state.channels[$ch].avg_per_5m
# update moving average gently
$state.channels[$ch].avg_per_5m = [Math]::Round(($avg * 0.9) + ($currentCount * 0.1), 3)

# burst ratio
$ratio = 0.0
if ($avg -gt 0) { $ratio = $currentCount / $avg } else { $ratio = $currentCount }
if ($ratio -ge 4) { $vector.burstiness = -25; [void]$reasons.Add("burst_cluster") }
elseif ($ratio -ge 2) { $vector.burstiness = -12; [void]$reasons.Add("elevated_rate") }

# Final score
$base = 50
$score = $base +
$vector.source_trust +
$vector.content_novelty +
$vector.burstiness +
$vector.duplication_pressure +
$vector.risk_language +
$vector.schema_integrity

$score = Clamp $score 0 100

$verdict = "accept"
if ($score -lt 40) { $verdict = "quarantine" }
elseif ($score -lt 70) { $verdict = "downweight" }

# Attach epistemic info
$obs | Add-Member -NotePropertyName "epistemic" -NotePropertyValue ([ordered]@{
        score   = $score
        vector  = $vector
        signals = [ordered]@{
            content_hash    = $contentHash
            author_hash     = $authorHash
            seen_count_24h  = $seenContent
            channel_rate_5m = $currentCount
            token_entropy   = $entropy
        }
        verdict = $verdict
        reasons = @($reasons)
    }) -Force

# Emit events
$evt = [ordered]@{
    ts           = (Get-Date).ToUniversalTime().ToString("o")
    event_type   = "ece_scored"
    source       = $src
    channel      = $ch
    score        = $score
    verdict      = $verdict
    content_hash = $contentHash
    corr         = $null
}
Append-Jsonl $EventsFile $evt

if ($verdict -eq "quarantine") {
    Append-Jsonl $QuarantineFile $obs
}

# Persist state
$state.updated_at = (Get-Date).ToUniversalTime().ToString("o")
Write-Json $StateFile $state 12

# Output enriched observation
$obs | ConvertTo-Json -Depth 12
