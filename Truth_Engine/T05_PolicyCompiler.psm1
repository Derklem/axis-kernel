<#
.SYNOPSIS
  Axis Policy Compiler (Layer 5)
.DESCRIPTION
  Reads Immune State and Autonomy Config to compile a deterministic Policy Snapshot.
  Decouples "Meta-Policy" (Axis_Mind/Immune) from "Enforcement" (T08 Executor).
#>

$script:RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$script:PolicyDir = "D:\Infinite\Infinity\Runtime\Policy"
$script:ImmuneState = "D:\Infinite\Infinity\Runtime\Decision\immune_state.json"
$script:IdentityState = "D:\Infinite\Infinity\Runtime\Identity\Identity_State.json"
$script:Snapshot = Join-Path $script:PolicyDir "policy_snapshot.json"
$script:History = Join-Path $script:PolicyDir "policy_snapshot_history.jsonl"

# Ensure Policy Directory Exists
if (-not (Test-Path $script:PolicyDir)) { New-Item -ItemType Directory -Path $script:PolicyDir -Force | Out-Null }

function Get-JsonFile {
    param([string]$path)
    if (-not (Test-Path $path)) { return $null }
    try { return (Get-Content $path -Raw | ConvertFrom-Json) } catch { return $null }
}

function Get-CanonicalHash {
    param($obj)
    # create a stable JSON representation (sorted keys implied by depth-first traversal if strictly implemented, 
    # but for PowerShell simply minimizing whitespace + consistent ordering is "good enough" for v0.1 receipt)
    $json = $obj | ConvertTo-Json -Depth 10 -Compress
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $hash = $sha.ComputeHash($bytes)
    return "sha256:" + ([BitConverter]::ToString($hash) -replace "-", "").ToLower()
}

function Compile-PolicySnapshot {
    # 1. Gather Inputs
    $immune = Get-JsonFile $script:ImmuneState
    $identity = Get-JsonFile $script:IdentityState
    
    $driftEma = if ($immune -and $immune.drift_ema) { $immune.drift_ema } else { 0 }
    $qMode = if ($immune -and $immune.mode) { $immune.mode } else { 0 }
    $idAnomaly = if ($identity -and $identity.global_anomaly_ema) { $identity.global_anomaly_ema } else { 0 }
    
    # Lineage: Hash the input (Immune State) to prove provenance
    $immuneHash = "missing"
    if ($immune) {
        $immuneHash = Get-CanonicalHash -obj $immune
    }

    # 2. Hysteresis (Sticky Thresholds)
    # Read previous snapshot to determine current mode for damping (inputs.immune_q_mode reflects prior effective mode)
    $prevPolicy = Get-PolicySnapshot
    $prevMode = if ($prevPolicy -and $prevPolicy.inputs) { $prevPolicy.inputs.immune_q_mode } else { 0 }
    
    # Default Target: 0
    $targetMode = 0
    
    # Hysteresis Logic:
    # Q0 -> Q1 if Drift > 30
    # Q1 -> Q0 if Drift < 20 (Damping gap of 10)
    # Q1 -> Q2 if Drift > 60
    # Q2 -> Q1 if Drift < 50
    
    if ($prevMode -eq 0) {
        if ($driftEma -gt 30) { $targetMode = 1 }
    }
    elseif ($prevMode -eq 1) {
        if ($driftEma -gt 60) { $targetMode = 2 }
        elseif ($driftEma -lt 20) { $targetMode = 0 }
        else { $targetMode = 1 } # Stick
    }
    elseif ($prevMode -ge 2) {
        if ($driftEma -lt 50) { $targetMode = 1 }
        else { $targetMode = 2 } # Stick
    }

    # Use the damped target mode
    $qMode = $targetMode

    
    # Defaults
    $posture = "NORMAL"
    $wrapperReq = $false
    $postEnabled = $true
    
    # 3. Capabilities Map
    
    # Q1: Trace (Wrapper Required)
    if ($qMode -eq 1) {
        $posture = "TRACE"
        $wrapperReq = $true
    }
    # Q2: Block Mutation (But allow local)
    elseif ($qMode -eq 2) {
        $posture = "BLOCK_MUTATION"
        $postEnabled = $false
    }
    # Q3: Freeze
    elseif ($qMode -ge 3) {
        $posture = "FREEZE"
        $postEnabled = $false
        $wrapperReq = $true
    }
    
    # Override based on high drift even if Q-Mode lags (Safety Valve)
    if ($driftEma -gt 80) { $postEnabled = $false; $posture = "DRIFT_OVERRIDE_BLOCK" }
    
    # Identity Anomaly Override
    if ($idAnomaly -gt 50) {
        $postEnabled = $false
        $posture = "IDENTITY_ANOMALY_LOCKDOWN"
    }

    # 4. Construct Snapshot
    $snap = [ordered]@{
        schema = "axis.policy_snapshot.v0.1"
        ts_utc = (Get-Date).ToUniversalTime().ToString("o")
        valid_until_ts = (Get-Date).AddSeconds(90).ToUniversalTime().ToString("o") # P12: 90s Validity Window
        kernel_seq = (Get-Random -Minimum 1000 -Maximum 9999) # Placeholder for real kernel seq
        inputs = @{
            immune_hash = $immuneHash
            immune_q_mode = $qMode
            allowed_mutations = @{
                POST       = @{
                    enabled = $postEnabled
                    # Hardcoded safe lists for v0.1
                    targets = @(
                        @{ pattern = "moltbook:introductions"; constraint = "EXACT" },
                        @{ pattern = "moltbook:general"; constraint = "EXACT" }
                    )
                }
                FILE_WRITE = @{ enabled = $true }
            }
        }
    }

    # 5. Canonicalize
    $hash = Get-CanonicalHash -obj $policy
    $policy["snapshot_id"] = $hash
    
    return $policy
}

function Write-PolicySnapshot {
    param($policy)
    
    if (-not $policy) { $policy = Compile-PolicySnapshot }
    
    $json = $policy | ConvertTo-Json -Depth 10
    
    # Linear History
    $json | Add-Content $script:History -Encoding UTF8

    # Atomic Pointer Update
    $tmp = $script:Snapshot + ".tmp"
    $json | Set-Content $tmp -Encoding UTF8 -Force
    Move-Item $tmp $script:Snapshot -Force
    
    return $policy
}

function Get-PolicySnapshot {
    $p = Get-JsonFile $script:Snapshot
    # Fallback if missing: Compile ephemeral safe Q0 policy
    if (-not $p) { return (Compile-PolicySnapshot) }
    return $p
}

Export-ModuleMember -Function Compile-PolicySnapshot, Write-PolicySnapshot, Get-PolicySnapshot
