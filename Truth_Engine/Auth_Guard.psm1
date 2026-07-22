<#
.SYNOPSIS
  Auth_Guard.psm1
  Enforces L3.2 Strict Auth Sentinel Logic.
  Rule: NO ACTION without L0 PROOF of ACTIVE_CLAIMED state.
#>

$RuntimeDir = "D:\Infinite\Infinity\Runtime\Moltbook"
$StateFile = Join-Path $RuntimeDir "auth_state.json"
$EventsFile = Join-Path $RuntimeDir "auth_events.jsonl"

function Get-AuthState {
    if (Test-Path $StateFile) {
        return (Get-Content $StateFile -Raw | ConvertFrom-Json)
    }
    return $null
}

function Write-AuthEvent {
    param($Type, $Reason, $Details = @{})
    
    $evt = [ordered]@{
        ts         = (Get-Date).ToUniversalTime().ToString("o")
        event_type = $Type
        reason     = $Reason
        details    = $Details
        meta       = @{ enforcement_layer = "AuthGuard"; confidence = 1.0 }
    }
    $evt | ConvertTo-Json -Compress | Add-Content $EventsFile -Encoding UTF8
}

function Test-AuthWriteAllowed {
    param(
        [string]$Action,
        $Target,
        $Intent
    )

    $state = Get-AuthState
    
    # 1. Enforcement Mode Check
    $mode = if ($state.enforcement_mode) { $state.enforcement_mode } else { "STRICT" }
    
    if ($mode -eq "WITNESS") {
        # WITNESS MODE: Log but Allow
        # We check the strict rules anyway to emit the correct warning/meta-log, but we return $true
        
        $strictPass = $true
        $failReason = ""
        
        if ($state.auth_state -ne "ACTIVE_CLAIMED") { $strictPass = $false; $failReason += "[State!=ACTIVE] " }
        if ($state.proof.class -ne "L0_OBSERVED") { $strictPass = $false; $failReason += "[Proof!=L0] " }
        
        try {
            $lastProof = Parse-ObservedTsUtc -ts ([string]$state.proof.observed_ts)
            $ttl = 0
            try { $ttl = [int]$state.proof.ttl_seconds } catch { $ttl = 0 }
            
            if ($lastProof) {
                if ($lastProof -isnot [DateTimeOffset]) { $lastProof = [DateTimeOffset]$lastProof }
                if ((Get-UtcNow) -gt $lastProof.AddSeconds($ttl)) { 
                    $strictPass = $false; $failReason += "[TTL_Expired] " 
                }
            }
            else {
                $strictPass = $false; $failReason += "[Bad_Date] " 
            }
        }
        catch { $strictPass = $false; $failReason += "[Exception] " }

        if (-not $strictPass) {
            Write-Warning "[AuthSentinel:WITNESS] ALLOWING ACTION despite violation: $failReason"
            # We allow it. The Sentinel witnesses the act.
            return $true
        }
    }

    # STRICT MODE (Default)
    # 2. State Check - Must be ACTIVE_CLAIMED
    if (-not $state -or $state.auth_state -ne "ACTIVE_CLAIMED") {
        Write-Warning "[AuthSentinel] Blocked: State is $(if($state){$state.auth_state}else{'UNKNOWN'})"
        return $false
    }

    # 2. Strict Proof Validation (Prevent Narrative Drift)
    if ($state.proof.class -ne "L0_OBSERVED") {
        Write-Warning "[AuthSentinel] Blocked: Non-L0 Proof Class ($($state.proof.class))"
        return $false
    }
    
    if ($state.proof.source_of_truth -ne "moltbook:status_result") {
        Write-Warning "[AuthSentinel] Blocked: Untrusted Proof Source ($($state.proof.source_of_truth))"
        return $false
    }
    
    # 3. TTL Check (Strict - Patched with DateTimeOffset)
    if (-not (Test-ProofTtlValid -state $state)) {
        # Optional: compute and print diagnostic values
        $obs = Parse-ObservedTsUtc -ts ([string]$state.proof.observed_ts)
        $ttlSec = 0; try { $ttlSec = [int]$state.proof.ttl_seconds } catch {}
        $now = Get-UtcNow
        $expiry = $null
        if ($obs -and $ttlSec -gt 0) {
            if ($obs -isnot [DateTimeOffset]) { $obs = [DateTimeOffset]$obs }
            $expiry = $obs.AddSeconds($ttlSec)
        }

        # Prepare log values safely for PS 5.1 (No ternary operators)
        $obsStr = "null"
        if ($obs) { try { $obsStr = $obs.ToString("o") } catch { $obsStr = [string]$obs } }

        $expStr = "null"
        if ($expiry) { try { $expStr = $expiry.ToString("o") } catch { $expStr = [string]$expiry } }

        Write-Warning ("[AuthSentinel] Blocked: Proof Expired (TTL) now={0:o} observed={1} ttl_seconds={2} expiry={3}" -f `
                $now, $obsStr, $ttlSec, $expStr)
        return $false
    }
    
    return $true
}

# --- Internal Helpers ---
function Get-UtcNow {
    return [DateTimeOffset]::UtcNow
}

function Parse-ObservedTsUtc {
    param([string]$ts)
    if ([string]::IsNullOrWhiteSpace($ts)) { return $null }

    # Handle ISO 8601 with Z properly
    try { return [DateTimeOffset]::Parse($ts, [Globalization.CultureInfo]::InvariantCulture, [Globalization.DateTimeStyles]::AssumeUniversal).ToUniversalTime() }
    catch {
        # Fallback: older PowerShell sometimes likes DateTime
        try { return ([DateTime]::Parse($ts)).ToUniversalTime() }
        catch { return $null }
    }
}

function Test-ProofTtlValid {
    param($state)

    if (-not $state -or -not $state.proof) { return $false }

    $obs = Parse-ObservedTsUtc -ts ([string]$state.proof.observed_ts)
    if (-not $obs) { return $false }

    # Ensure TTL is numeric seconds
    $ttlSec = 0
    try { $ttlSec = [int]$state.proof.ttl_seconds } catch { $ttlSec = 0 }
    if ($ttlSec -le 0) { return $false }

    $expiry = $obs.AddSeconds($ttlSec)
    $now = Get-UtcNow

    # Convert $obs to DateTimeOffset if fallback returned DateTime
    if ($obs -isnot [DateTimeOffset]) { $obs = [DateTimeOffset]$obs; $expiry = $obs.AddSeconds($ttlSec) }

    return ($now -le $expiry)
}

Export-ModuleMember -Function Get-AuthState, Test-AuthWriteAllowed, Write-AuthEvent
