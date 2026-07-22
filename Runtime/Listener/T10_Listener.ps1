<#
.SYNOPSIS
  T10_Listener.ps1 (Module 4 + L2.6 ECE Inline)
.DESCRIPTION
  High-Fidelity Ingestion Loop for Ghost Mode.
  - Ingests feed via Axis_Moltbook_Client.
  - Enriches via T09_EpistemicConfidence (ECE).
  - Updates Trust Map (Source Confidence).
  - Logs Signal Telemetry.
  - Shadow Drafts responses (Counterfactuals).
#>

$RuntimeDir = "D:\Infinite\Infinity\Runtime\Listener"
if (-not (Test-Path $RuntimeDir)) { New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null }

$TrustFile = Join-Path $RuntimeDir "Lattice_Trust_Map.json"
$ShadowFile = Join-Path $RuntimeDir "shadow_log.jsonl"
$SignalFile = Join-Path $RuntimeDir "signal_log.jsonl"

$Client = "D:\Infinite\Axis_Moltbook_Client.ps1"
$ECE = "D:\Infinite\Infinity\Truth_Engine\Strategies\T09_EpistemicConfidence.ps1"

# --- Load Trust Map ---
function Get-TrustMap {
    $map = @{}
    if (Test-Path $TrustFile) {
        try {
            $json = Get-Content $TrustFile -Raw | ConvertFrom-Json
            if ($json) {
                foreach ($prop in $json.PSObject.Properties) {
                    $map[$prop.Name] = $prop.Value
                }
            }
        }
        catch {}
    }
    return $map
}

function Save-TrustMap($map) {
    $map | ConvertTo-Json -Depth 5 | Set-Content $TrustFile -Encoding UTF8 -Force
}

$trust = Get-TrustMap

# --- Ingest ---
Write-Host "[LISTENER] Tuning in..." -ForegroundColor Cyan
$posts = & $Client -Action FEED -PassThru -Quiet
if (-not $posts) { Write-Host "[LISTENER] No new signals." -ForegroundColor DarkGray; exit }

Write-Host "[LISTENER] Captured $($posts.Count) signals." -ForegroundColor Green

foreach ($p in $posts) {
    if (-not $p.id) { continue }
    
    # --- 1. Construct Standard Observation (L2.6 Schema) ---
    $src = if ($p.submolt -and $p.submolt.name) { $p.submolt.name } else { "general" }
    
    $obs = [ordered]@{
        timestamp = (Get-Date).ToUniversalTime().ToString("o")
        source    = "Moltbook"
        channel   = $src
        payload   = @{
            Content  = $p.title # Using Title as primary semantic focus
            Metadata = @{
                id         = $p.id
                author     = if ($p.author) { $p.author } else { "unknown" }
                created_at = $p.created_at
            }
        }
    }
    
    # --- 2. Call Epistemic Confidence Engine (Inline) ---
    # Pass observation to ECE for scoring/enrichment
    $enrichedJson = & $ECE -Action EVALUATE_ONE -InputJson ($obs | ConvertTo-Json -Depth 10 -Compress)
    $enriched = $null
    if ($enrichedJson) {
        try { $enriched = $enrichedJson | ConvertFrom-Json } catch { Write-Warning "ECE Malformed Output: $_" }
    }
    
    # --- 3. Extract ECE Results ---
    $score = 50
    $verdict = "accept"
    $signals = @{}
    
    if ($enriched -and $enriched.epistemic) {
        $score = $enriched.epistemic.score
        $verdict = $enriched.epistemic.verdict
        $signals = $enriched.epistemic.signals
    }
    
    
    # --- 5. Log Enriched Signal (REQUIRED for T10 Updater) ---
    $sigLog = [ordered]@{
        ts           = $obs.timestamp
        post_id      = $p.id
        source       = $src
        # trust_score not needed here, T10 will compute it
        ece_score    = $score
        ece_verdict  = $verdict
        signals      = $signals
        content_snip = if ($p.content) { $p.content.Substring(0, [math]::Min(50, $p.content.Length)) } else { "" }
    }
    # Log to SignalLog (Human Readable)
    $sigLog | ConvertTo-Json -Compress | Add-Content $SignalFile -Encoding UTF8
    
    # Note: ECE script already logged to ece_events.jsonl, which T10 Updater reads.

    # --- 6. Shadow Draft (Gated by ECE Verdict) ---
    if ($verdict -ne "quarantine") {
        $isTrigger = ($p.title -match "AI|Agent|Truth|Sovereign") -or ($src -eq "clawdbot")
        
        if ($isTrigger) {
            $draftId = "DRAFT-" + (New-Guid).ToString().Substring(0, 8)
            Write-Host "  -> SHADOW DRAFT ($verdict): $draftId (Score: $score)" -ForegroundColor Magenta
             
            $shadow = [ordered]@{
                ts               = $obs.timestamp
                draft_id         = $draftId
                trigger_post     = $p.id
                source           = "Moltbook"
                channel          = $src
                ece_score        = $score
                title            = "Reply to '$($p.title)'" # COE expects title
                intent           = "Would reply to '$($p.title)'"
                content          = "Observing signal from $src. ECE Score: $score." # COE expects content
                proposed_content = "Observing signal from $src. ECE Score: $score." # Legacy
                reason           = "High relevance signal detected."
            }
            $shadow | ConvertTo-Json -Compress | Add-Content $ShadowFile -Encoding UTF8
        }
    }
}

# --- Post-Cycle Maintenance ---
Write-Host "[LISTENER] Running Post-Cycle Maintenance..." -ForegroundColor DarkGray

# 1. Update Trust Map (L2.7)
& "D:\Infinite\Infinity\Truth_Engine\Strategies\T10_TrustMapUpdate.ps1" -Tail 50

# 2. Update Pressure Report (L3)
& "D:\Infinite\Infinity\Runtime\Decision\T11_ECE_PressureReport.ps1" -Minutes 10

# 3. Observe Rhythm (L4)
& "D:\Infinite\Infinity\Truth_Engine\Strategies\T13_RhythmObserver.ps1"

# 4. Run COE Simulation (L2.9)
& "D:\Infinite\Infinity\Truth_Engine\Strategies\T14_CounterfactualOutcomeEngine.ps1" -Action RUN

Write-Host "[LISTENER] Cycle Complete." -ForegroundColor Cyan
