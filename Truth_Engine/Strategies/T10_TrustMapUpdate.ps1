<#
.SYNOPSIS
  T10_TrustMapUpdate.ps1 (L2.7)
.DESCRIPTION
  Deterministic trust learner from ECE events:
  - Reads ece_events.jsonl
  - Updates Lattice_Trust_Map.json
  - Bounded trust [0.05..0.95], annealed alpha
#>

param(
    [int]$Tail = 200,
    [string]$EpistemicDir = "D:\Infinite\Infinity\Runtime\Epistemic",
    [string]$TrustMapPath = "D:\Infinite\Infinity\Runtime\Listener\Lattice_Trust_Map.json", # Fixed path to match existing
    [string]$LogPath = "D:\Infinite\Infinity\Runtime\Listener\trust_update_log.jsonl"
)

function Ensure-Dir([string]$p) { if (-not(Test-Path $p)) { New-Item -ItemType Directory -Path $p -Force | Out-Null } }
function Clamp([double]$v, [double]$a, [double]$b) { if ($v -lt $a) { $a }else { if ($v -gt $b) { $b }else { $v } } }

Ensure-Dir (Split-Path $TrustMapPath -Parent)
Ensure-Dir (Split-Path $LogPath -Parent)

$eventsFile = Join-Path $EpistemicDir "ece_events.jsonl"
if (-not(Test-Path $eventsFile)) { Write-Host "No ece_events.jsonl"; return }

# --- Load Trust Map (Hashtable conversion for safety) ---
$trust = $null
if (Test-Path $TrustMapPath) {
    try { 
        $json = Get-Content $TrustMapPath -Raw | ConvertFrom-Json 
        # Convert to Hashtable/Ordered for dynamic access
        $trust = [ordered]@{
            version    = if ($json.version) { $json.version } else { "1.0" }
            updated_at = if ($json.updated_at) { $json.updated_at } else { (Get-Date).ToUniversalTime().ToString("o") }
            baseline   = if ($json.baseline) { $json.baseline } else { 0.50 }
            items      = [ordered]@{}
        }
        
        # Handle existing items structure OR the legacy flat structure I created in Module 4
        # My Module 4 structure was flat: { "tech": {score...}, "general": {score...} }
        # The new Spec wants: { items: { "Moltbook::tech": {trust...} } }
        # I must migrate or adapt.
        # Let's Adapt: Read flat keys, migrate them to 'items' if needed, or support new schema.
        
        # Actually, let's migrate.
        if ($json.PSObject.Properties["items"]) {
            # already new schema
            foreach ($p in $json.items.PSObject.Properties) { $trust.items[$p.Name] = $p.Value }
        }
        else {
            # Migration from Module 4 schema
            foreach ($p in $json.PSObject.Properties) {
                if ($p.Name -in "version", "updated_at", "baseline") { continue }
                # Assume Moltbook source for legacy keys
                $newKey = "Moltbook::$($p.Name)" 
                $trust.items[$newKey] = [ordered]@{
                    trust        = if ($p.Value.score) { $p.Value.score } else { 0.5 }
                    n            = if ($p.Value.count) { $p.Value.count } else { 0 }
                    last_updated = if ($p.Value.last_seen) { $p.Value.last_seen } else { (Get-Date).ToUniversalTime().ToString("o") }
                }
            }
        }
    }
    catch { $trust = $null }
}

if (-not $trust) {
    $trust = [ordered]@{
        version    = "1.0"
        updated_at = (Get-Date).ToUniversalTime().ToString("o")
        baseline   = 0.50
        items      = [ordered]@{}
    }
}

$lines = Get-Content $eventsFile -Tail $Tail
foreach ($line in $lines) {
    try { $e = $line | ConvertFrom-Json } catch { continue }
    if ($e.event_type -ne "ece_scored") { continue }

    $source = if ($e.source) { [string]$e.source } else { "unknown" }
    $channel = if ($e.channel) { [string]$e.channel } else { "unknown" }
    $key = "$source::$channel"

    $score = [int]$e.score
    $scoreNorm = [double]$score / 100.0

    if (-not $trust.items.Contains($key)) {
        $trust.items[$key] = [ordered]@{
            trust        = [double]$trust.baseline
            n            = 0
            last_updated = (Get-Date).ToUniversalTime().ToString("o")
        }
    }

    $item = $trust.items[$key]
    $n = [int]$item.n
    # Alpha decay: 1/(20+n). Starts at 1/20=0.05. Decays as N grows.
    $alpha = [Math]::Min(0.05, 1.0 / [double]([Math]::Max(20, $n + 1)))

    $old = [double]$item.trust
    $new = ($old * (1.0 - $alpha)) + ($scoreNorm * $alpha)
    $new = Clamp $new 0.05 0.95

    $item.trust = [Math]::Round($new, 3)
    $item.n = $n + 1
    $item.last_updated = (Get-Date).ToUniversalTime().ToString("o")

    # log changes
    $log = [ordered]@{
        ts         = (Get-Date).ToUniversalTime().ToString("o")
        event_type = "trust_update"
        key        = $key
        old        = [Math]::Round($old, 3)
        new        = [Math]::Round($new, 3)
        alpha      = [Math]::Round($alpha, 4)
        score      = $score
    }
    ($log | ConvertTo-Json -Compress) | Add-Content $LogPath -Encoding UTF8
}

$trust.updated_at = (Get-Date).ToUniversalTime().ToString("o")
($trust | ConvertTo-Json -Depth 8) | Set-Content $TrustMapPath -Encoding UTF8 -Force
Write-Host "Trust map updated via T10." -ForegroundColor Cyan
