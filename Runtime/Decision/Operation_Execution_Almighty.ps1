<#
.SYNOPSIS
  Operation_Execution_Almighty.ps1
  The Sovereign orchestrator. Unifies Meaning (Resonance) and Muscle (Execution).
  v27.3: Authority State Machine (Atomized), Hysteresis, and Structural Health.
#>

$ScriptRoot = "D:\Infinite"
. "$ScriptRoot\Axis_FS_Lib.ps1"

# Paths
$ContractPath = "$ScriptRoot\Infinity\Autonomy_Contract.json"
$ResonancePath = "$ScriptRoot\Infinity\Runtime\Decision\Resonance_State.json"
$QueuePath = "$ScriptRoot\Infinity\Runtime\Decision\intent_queue.jsonl"
$ApprovedPath = "$ScriptRoot\Infinity\Runtime\Decision\approved_intents.jsonl"
$PulsePath = "$ScriptRoot\Infinity\Runtime\Decision\Sovereign_Pulse.json"
$IdentityRegistryPath = "$ScriptRoot\Infinity\Runtime\Identity\identity_registry.json"

Write-Output "[ALMIGHTY] Initializing Sovereign Spine v27.3 (Unified State Machine)..."

# --- 1. Helplers ---
function Get-StructuralHealth {
    $health = @{ ok = $true; flags = @() }
    $checkFiles = @($ContractPath, $ResonancePath)
    foreach ($f in $checkFiles) {
        if (-not (Test-Path $f)) { $health.ok = $false; $health.flags += "MISSING_$(Split-Path $f -Leaf)" }
    }
    return $health
}

function Invoke-IntentNormalization($rawObj) {
    if ($null -eq $rawObj -or $rawObj -is [string] -or $rawObj -is [array]) { return $null }
    $normalized = [pscustomobject]@{
        identity = "unknown"; intent_id = $null; correlation_id = $null; payload_type = $null; budget_token = "unassigned"; seed_source = $null
        risk_class = $null; crypto_mode = "NONE"; payload = $null; reality = $null; is_envelope = $false; raw = $rawObj
    }
    if ($rawObj.schema -like "axis.intent_envelope.*") {
        $normalized.is_envelope = $true
        $normalized.identity = if ($null -ne $rawObj.identity) { [string]$rawObj.identity } else { "unknown" }
        $normalized.correlation_id = if ($null -ne $rawObj.correlation_id) { [string]$rawObj.correlation_id } else { $null }
        try { $inner = if ($rawObj.intent_json) { $rawObj.intent_json | ConvertFrom-Json } else { $null } } catch { return $null }
        if ($null -ne $inner) {
            $normalized.payload = $inner.payload; $normalized.reality = $inner.reality
            $normalized.intent_id = if ($null -ne $inner.intent_id) { $inner.intent_id } elseif ($null -ne $inner.payload) { $inner.payload.id } else { $null }
            $normalized.payload_type = if ($null -ne $inner.type) { $inner.type } elseif ($null -ne $inner.payload) { $inner.payload.type } else { $null }
        }
    }
    elseif ($rawObj.payload) {
        $normalized.payload = $rawObj.payload; $normalized.reality = $rawObj.reality
        $normalized.identity = if ($null -ne $rawObj.reality -and $null -ne $rawObj.reality.source) { [string]$rawObj.reality.source } else { "unknown" }
        $normalized.correlation_id = if ($null -ne $rawObj.correlation_id) { [string]$rawObj.correlation_id } elseif ($null -ne $rawObj.corr_id) { [string]$rawObj.corr_id } else { $null }
        $normalized.intent_id = if ($null -ne $rawObj.intent_id) { $rawObj.intent_id } else { $rawObj.payload.id }
        $normalized.payload_type = if ($null -ne $rawObj.type) { $rawObj.type } else { $rawObj.payload.type }
    }
    else { return $null }
    return $normalized
}

function Get-IdentityTierCeiling($identity, $reg) {
    if ([string]::IsNullOrWhiteSpace($identity) -or $identity -eq "unknown") { return 0 }
    $identity = $identity.ToLowerInvariant()
    if ($null -eq $reg -or $null -eq $reg.identities) { return 0 }
    $idProp = $null
    if ($null -ne $reg.identities.PSObject) { $idProp = $reg.identities.PSObject.Properties[$identity] }
    if ($idProp) {
        $idRecord = $idProp.Value
        if ($idRecord.crypto_mode -eq "DEV_SHARED_SECRET") { return 0 }
        return [int]$idRecord.tier
    }
    return 0
}

# --- 2. Mainframe ---
$lockBlock = Invoke-WithMutex -Name "Global\Axis_Orchestrator_Mutex_v2" -TimeoutMs 5000 -ScriptBlock {
    # a. Load Core State
    $contract = Get-SafeJson -Path $ContractPath
    $resState = Get-SafeJson -Path $ResonancePath
    $idReg = Get-SafeJson -Path $IdentityRegistryPath
    $pulse = Get-SafeJson -Path $PulsePath

    if (-not $contract) { throw "Autonomy Contract missing at $ContractPath" }
    if (-not $resState) { throw "Resonance State missing at $ResonancePath" }

    # b. Initialize Pulse
    $health = Get-StructuralHealth
    if (-not $pulse -or -not $pulse.authority_state) {
        $pulse = [pscustomobject]@{
            epoch_start_utc   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:00:00Z")
            authority_state   = "STABLE"
            tier_cap          = 1
            intent_counts     = [pscustomobject]@{"tier0" = 0; "tier1" = 0; "tier2" = 0; "tier3" = 0 }
            token_counts      = [pscustomobject]@{}
            error_count       = 0
            dwell_cycles      = [pscustomobject]@{"tier1" = 0; "tier2" = 0; "tier3" = 0 }
            resonance_history = @()
            concurrency       = [pscustomobject]@{ queue_lock_wait_ms = @(); rewrite_count = 0; overlap_prevented = 0; duplicate_blocked = 0; mutex_timeout_count = 0 }
        }
    }

    # c. Authority State Machine (Atomized)
    $score = [double]$resState.score
    $pulse.resonance_history = ($pulse.resonance_history + $score) | Select-Object -Last 10
    $avgRes = ($pulse.resonance_history | Measure-Object -Average).Average

    $totalExecuted = 0
    foreach ($p in $pulse.intent_counts.PSObject.Properties) { $totalExecuted += [int]$p.Value }
    
    if ($totalExecuted -ge $contract.quotas.min_attempts_for_incident) {
        $errPct = if ($totalExecuted -gt 0) { ($pulse.error_count / $totalExecuted) * 100 } else { 0 }
        if ($errPct -ge $contract.quotas.auto_downgrade_error_pct -or -not $health.ok) {
            Write-Warning "[ALMIGHTY] DOWNGRADED -> LOCKDOWN ($($health.flags -join ' '))"
            $pulse.authority_state = "LOCKDOWN"; $pulse.tier_cap = 0
        }
    }

    if ($pulse.authority_state -ne "LOCKDOWN") {
        foreach ($tid in ("1", "2", "3")) {
            $tierDef = $contract.tier_definitions."$tid"
            $currentCap = [int]$pulse.tier_cap
            if ($currentCap -ge [int]$tid -and $score -lt $tierDef.lock_resonance) {
                Write-Warning "[ALMIGHTY] Tier $tid LOCKED"
                $pulse.tier_cap = [int]$tid - 1; $pulse.dwell_cycles."tier$tid" = 0
            }
            if ($currentCap -lt [int]$tid -and $score -ge $tierDef.unlock_resonance) {
                $pulse.dwell_cycles."tier$tid"++
                $reqDwell = if ($null -ne $tierDef.dwell_time_min) { [int]$tierDef.dwell_time_min } else { 0 }
                if ($pulse.dwell_cycles."tier$tid" -ge $reqDwell) {
                    Write-Output "[ALMIGHTY] Tier $tid UNLOCKED"
                    $pulse.tier_cap = [int]$tid
                    $pulse.authority_state = if ([int]$tid -ge 2) { "ESCALATED" } else { "STABLE" }
                }
            }
            else { if ($score -lt $tierDef.unlock_resonance) { $pulse.dwell_cycles."tier$tid" = 0 } }
        }
    }

    Write-Output "[ALMIGHTY] State: $($pulse.authority_state) | Cap: $($pulse.tier_cap) | Res: $score"

    # d. Process Queue
    if (-not (Test-Path $QueuePath)) { 
        Write-AtomicJson -Path $PulsePath -Data $pulse
        return 
    }

    $rawIntents = @()
    try {
        $lines = Get-Content $QueuePath
        foreach ($line in $lines) { if (-not [string]::IsNullOrWhiteSpace($line)) { $rawIntents += $line | ConvertFrom-Json } }
    }
    catch { return }

    $remaining = New-Object System.Collections.Generic.List[PSObject]
    foreach ($raw in $rawIntents) {
        $intent = Invoke-IntentNormalization -rawObj $raw
        if ($null -eq $intent) { continue }
        
        $intentTier = 0
        foreach ($tid in ("1", "2", "3")) { if ($intent.payload_type -match $contract.tier_definitions."$tid".match) { $intentTier = [int]$tid } }
        
        $tierLimit = [int]$contract.quotas.per_tier."$intentTier"
        $tierUsed = [int]$pulse.intent_counts."tier$intentTier"
        
        $identityReservedTier = Get-IdentityTierCeiling -identity $intent.identity -reg $idReg
        $authorized = ($intentTier -le [int]$pulse.tier_cap) -and ($intentTier -le $identityReservedTier)
        
        if ($authorized -and $tierUsed -lt $tierLimit) {
            Write-Output "[ALMIGHTY] Approving [T$intentTier]: $($intent.intent_id)"
            $intent | Add-Member -NotePropertyName "status" -NotePropertyValue "APPROVED_SOVEREIGN" -Force
            $intent | Add-Member -NotePropertyName "approved_at" -NotePropertyValue (Get-Date).ToUniversalTime().ToString("o") -Force
            $intent | Add-Member -NotePropertyName "risk_tier" -NotePropertyValue $intentTier -Force
            
            $intentJson = $intent | ConvertTo-Json -Compress
            $hash = ([System.BitConverter]::ToString(([System.Security.Cryptography.SHA256]::Create()).ComputeHash([System.Text.Encoding]::UTF8.GetBytes($intentJson)))).Replace("-", "").ToLower()
            $intent | Add-Member -NotePropertyName "audit_hash" -NotePropertyValue $hash -Force

            Append-JsonlLineNoBom -Path $ApprovedPath -Data $intent
            $pulse.intent_counts."tier$intentTier"++
        }
        else {
            $remaining.Add($raw)
        }
    }

    # e. Save & Cleanup
    $pulse.concurrency.rewrite_count++
    Write-AtomicJson -Path $PulsePath -Data $pulse

    if ($remaining.Count -eq 0) {
        if (Test-Path $QueuePath) { Remove-Item $QueuePath -Force }
    }
    else {
        $temp = "$QueuePath.tmp"
        if (Test-Path $temp) { Remove-Item $temp -Force }
        foreach ($rem in $remaining) { Append-JsonlLineNoBom -Path $temp -Data $rem }
        [System.IO.File]::Replace($temp, $QueuePath, "$QueuePath.bak")
        if (Test-Path "$QueuePath.bak") { Remove-Item "$QueuePath.bak" -Force }
    }

    # f. Reflective Observation (Phase 23)
    Write-Output "[ALMIGHTY] Triggering Reflective Observation Cycle..."
    try {
        # Generate Proposals
        python.exe "$ScriptRoot\emit_optimization_proposal.py"
        # Adjudicate Pending Proposals
        python.exe "$ScriptRoot\admit_optimization_proposal.py"
    } catch {
        Write-Warning "[ALMIGHTY] Reflective Cycle Failed: $_"
    }

    # Trigger T08 (Disabled for Kill-Testing Phase 7.3)
}

if (-not $lockBlock.lock_acquired) {
    Write-Warning "[ALMIGHTY] Orchestrator Mutex Timeout. Skipping cycle."
    exit 1
}
