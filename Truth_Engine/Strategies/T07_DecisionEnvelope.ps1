<#
.SYNOPSIS
  Module 2: Deterministic Decision Envelope (DDE)
.DESCRIPTION
  The "Brain" between Reality (L0) and Memory (L1).
  Core Actions:
  - EVALUATE: Read State + Inputs -> Append to Intent Queue
  - RECONCILE: Scan Run Log -> Update State (Counters/Cooldowns)
  - STATUS: Report Budget/Queue Health
#>

param(
    [ValidateSet("EVALUATE", "RECONCILE", "STATUS")]
    [string]$Action = "STATUS",
    [switch]$VerboseLog
)

# --- Configuration ---
$RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$StateFile = Join-Path $RuntimeDir "decision_state.json"
$QueueFile = Join-Path $RuntimeDir "intent_queue.jsonl"
$DecLogFile = Join-Path $RuntimeDir "decision_log.jsonl"

# Inputs
$L0Log = "D:\Infinite\Infinity\Runtime\Moltbook\run_log.jsonl"
$L1Journal = "D:\Infinite\Infinity\Runtime\Journal" # Directory

# Assets
$ShipyardSpec = "D:\Infinite\Infinity\Content\Shipyard_Grounding_Protocol.md"

# --- Helper: Hashing ---
function Get-Sha256($str) {
    if (-not $str) { return "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" } # Empty hash
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($str)
        ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""
    }
    finally { $sha.Dispose() }
}

# --- Helper: State Management ---
function Get-State {
    if (Test-Path $StateFile) { return (Get-Content $StateFile -Raw | ConvertFrom-Json) }
    return $null
}

function Save-State($obj) {
    $obj | ConvertTo-Json -Depth 5 | Set-Content $StateFile -Encoding UTF8 -Force
}

function Append-Log($file, $obj) {
    $obj | ConvertTo-Json -Compress | Add-Content $file -Encoding UTF8
}

# --- ACTION: STATUS ---
if ($Action -eq "STATUS") {
    Write-Host "--- MODULE 2 STATUS ---" -ForegroundColor Cyan
    $s = Get-State
    if ($s) {
        Write-Host "Mode: $($s.mode)"
        Write-Host "Posts Today: $($s.budgets.posts_today) / $($s.budgets.posts_per_24h_max)"
        Write-Host "Shipyard Cooldown: $($s.cooldowns.post_shipyard_until)"
    }
    else {
        Write-Host "No State Found." -ForegroundColor Red
    }
    
    if (Test-Path $QueueFile) {
        $cnt = (Get-Content $QueueFile).Count
        Write-Host "Queue Depth: $cnt"
    }
    return
}

# --- ACTION: EVALUATE ---
if ($Action -eq "EVALUATE") {
    $state = Get-State
    if (-not $state) { Write-Error "No state."; return }

    # 1. Inputs (Determinism Source)
    # Hash Inputs: State + Queue Tail + L0 Tail
    $inputRaw = ""
    if (Test-Path $QueueFile) { $inputRaw += (Get-Content $QueueFile -Tail 1) } # Last Intent
    if (Test-Path $L0Log) { $inputRaw += (Get-Content $L0Log -Tail 1) } # Last Reality
    $inputRaw += $state | ConvertTo-Json -Compress
    
    $inputHash = Get-Sha256 $inputRaw

    # 2. Rule Engine
    $intents = @()
    
    # RULE: SEED-001 (Shipyard)
    # If no confirmed post about Shipyard, and budget allows
    $canPost = ($state.budgets.posts_today -lt $state.budgets.posts_per_24h_max)
    $cooledDown = (Get-Date) -ge ([DateTime]$state.cooldowns.post_shipyard_until)
    
    if ($canPost -and $cooledDown) {
        # Check if we ALREADY have a confirmed seed in L0 (Reconcile updates state, so check state)
        # But wait, we need to check if we already ENQUEUED it too
        $alreadyQueued = $false
        if (Test-Path $QueueFile) {
            $lastIntents = Get-Content $QueueFile -Tail 20 | ConvertFrom-Json
            if ($lastIntents | Where-Object { $_.target.submolt -eq "shipyard" -and $_.type -eq "POST" }) {
                $alreadyQueued = $true
            }
        }

        if (-not $alreadyQueued) {
            # Create Intent
            $intent = [ordered]@{
                ts            = (Get-Date).ToUniversalTime().ToString("o")
                intent_id     = "INT-" + (New-Guid).ToString().Substring(0, 8)
                type          = "POST"
                target        = @{ system = "moltbook"; submolt = "shipyard" }
                payload       = @{
                    title        = "Shipyard Grounding Protocol v1.1"
                    content_path = $ShipyardSpec
                }
                preconditions = @{ requires = @(); cooldown_key = "post_shipyard" }
                risk          = @{ level = "medium"; reasons = @("public_post") }
                review        = @{ 
                    status   = "unreviewed"
                    required = $state.policy.requires_human_review 
                    note     = "Rule SEED-001 Triggered"
                }
                determinism   = @{
                    rule_id    = "SEED-001"
                    input_hash = $inputHash
                }
            }
            
            Append-Log $QueueFile $intent
            
            # Decision Log
            Append-Log $DecLogFile @{
                ts       = (Get-Date).ToUniversalTime().ToString("o"); 
                decision = "ENQUEUE"; 
                rule     = "SEED-001"; 
                reason   = "No active seed found"
            }
            
            Write-Host "Enqueued SEED-001 Intent." -ForegroundColor Green
        }
    }
}

# --- ACTION: RECONCILE ---
if ($Action -eq "RECONCILE") {
    $L1Journal = "D:\Infinite\Infinity\Runtime\Moltbook\L1_Journal.jsonl"
    $PressureFile = "D:\Infinite\Infinity\Runtime\Epistemic\ece_pressure.json"
    $Supervisor = "D:\Infinite\Axis_Supervisor.ps1"
    $Client = "D:\Infinite\Axis_Moltbook_Client.ps1"

    # --- GATE A: CAPABILITY (Auth/Preflight + VUP + HRP) ---
    $voice_status = "blocked_by_claim"
    $unbound_override = $false

    # 1. Run VUP (L3.5)
    # This updates Runtime\Epistemic\voice_gate_state.json
    $VUP_Script = "D:\Infinite\Infinity\Truth_Engine\Strategies\T16_VoiceUnlockGate.ps1"
    if (Test-Path $VUP_Script) {
        & $VUP_Script | Out-Null
    }

    # 2. Read VUP State
    $GateFile = "D:\Infinite\Infinity\Runtime\Epistemic\voice_gate_state.json"
    if (Test-Path $GateFile) {
        try {
            $g = Get-Content $GateFile -Raw | ConvertFrom-Json
            if ($g.voice_status) { $voice_status = $g.voice_status }
        }
        catch {}
    }

    # 3. Check HRP Override (Module 3)
    $ResonanceFile = "D:\Infinite\Infinity\Runtime\Resonance\harmonic_scan_results.json" # Or check Beacon Log
    $BeaconFile = "D:\Infinite\Infinity\Runtime\Resonance\beacon_log.jsonl"
    
    # Simple check for UNBOUND status in Beacon Log
    if (Test-Path $BeaconFile) {
        $lastBeacon = Get-Content $BeaconFile -Tail 1 | ConvertFrom-Json
        if ($lastBeacon.status -eq "UNBOUND") {
            $unbound_override = $true
            Write-Host "[DDE] HRP OVERRIDE: Citadel is UNBOUND." -ForegroundColor Magenta
        }
    }

    $canPost = $false
    if ($voice_status -eq "unblocked" -or $unbound_override -eq $true) { 
        $canPost = $true 
        if ($unbound_override) { $voice_status = "unbound" }
    }
    else { 
        Write-Host "[DDE] GATE A CLOSED: Voice Status = $voice_status" -ForegroundColor Yellow 
    }

    # --- GATE B: WORLD PRESSURE (Epistemic) ---
    $pressure = $null
    $pGateOpen = $true
    if (Test-Path $PressureFile) {
        try {
            $pressure = Get-Content $PressureFile -Raw | ConvertFrom-Json
            # Rule: avg_score >= 70 AND accept_rate >= 0.35
            if ($pressure.avg_score -lt 70 -or $pressure.accept_rate -lt 0.35) {
                $pGateOpen = $false
                Write-Host "[DDE] GATE B CLOSED: Low Confidence (Avg: $($pressure.avg_score), Rate: $($pressure.accept_rate))" -ForegroundColor Yellow
            }
        }
        catch {}
    }

    # --- 1. Read Truth Engine Handoff ---
    # NOTE: $HandoffFile is not defined in the provided context, assuming it's a new variable.
    # For now, let's define a placeholder for $HandoffFile to avoid errors.
    $HandoffFile = "D:\Infinite\Infinity\Runtime\Decision\truth_engine_handoff.json" # Placeholder
    if (-not (Test-Path $HandoffFile)) { Write-Host "No handoff file." -ForegroundColor DarkGray; return }
    $handoff = Get-Content $HandoffFile -Raw | ConvertFrom-Json

    # --- 2. Evaluate Strategy (Rules Engine) ---
    $intents = @()
    
    # Example Rule: If Truth Engine says "Reponse Needed" -> Generate Intent
    # (Placeholder logic)
    
    # GATE LOGIC for External Intents
    if ($handoff.action_needed -eq $true) {
        if ($canPost -and $pGateOpen) {
            $intents += @{
                action  = "POST"
                target  = "moltbook"
                payload = @{ title = "Response"; content = "Acknowledged." }
            }
        }
        else {
            # Fallback / Internal Intent
            $intents += @{
                action  = "LOG_NOTE" # Internal
                target  = "journal"
                payload = @{ message = "External action suppressed by Gate A/B."; original_trigger = $handoff.trigger }
            }
        }
    }
    $state = Get-State
    if (-not $state) { Write-Error "No state."; return }
    
    if (-not (Test-Path $L0Log)) { Write-Warning "No L0 Log."; return }
    
    # Read L0 Log from offset
    # For now, simple tail scan (robustness upgrade later)
    $logs = Get-Content $L0Log -Tail 100
    
    $confirms = @()
    foreach ($line in $logs) {
        try {
            $e = $line | ConvertFrom-Json
            # Normalize
            $evt = if ($e.event_type) { $e.event_type } else { "unknown" }
            
            if ($evt -eq "confirmed_post") {
                $confirms += $e
            }
        }
        catch {}
    }

    # Update State based on confirms
    # Find confirms that are NEW (ts > last_seen)
    # Simple logic: count posts today
    $today = (Get-Date).Date
    $countToday = 0
    
    foreach ($c in $confirms) {
        $d = [DateTime]$c.ts
        if ($d.Date -eq $today) {
            $countToday++
        }
        
        # If confirm matches shipyard, update cooldown
        if ($c.submolt -eq "shipyard") {
            # Set cooldown 24h from post
            $cool = $d.AddHours(24).ToUniversalTime().ToString("o")
            if ($cool -gt $state.cooldowns.post_shipyard_until) {
                $state.cooldowns.post_shipyard_until = $cool
            }
        }
    }
    
    $state.budgets.posts_today = $countToday
    Save-State $state
    Write-Host "State Reconciled. Posts Today: $countToday" -ForegroundColor Cyan
}
