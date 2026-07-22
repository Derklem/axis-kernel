<#
.SYNOPSIS
    T08 Decision Log Policy Filter
.DESCRIPTION
    Loads decision_log_policy.json and provides a predicate to determine if a log entry should be emitted.
#>

$script:LogPolicy = $null
$script:LogPolicyPath = Join-Path "D:\Infinite\Infinity\Runtime\Decision" "decision_log_policy.json"

function Get-LogPolicy {
    if ($script:LogPolicy) { return $script:LogPolicy }
    if (Test-Path $script:LogPolicyPath) {
        try {
            $script:LogPolicy = Get-Content $script:LogPolicyPath -Raw | ConvertFrom-Json
            return $script:LogPolicy
        } catch {
            Write-Warning "[LogPolicy] Failed to parse: $($_.Exception.Message)"
        }
    }
    return $null
}

function Test-ShouldEmitLog {
    param(
        [string]$Mode,
        [string]$ResultCode
    )

    $policy = Get-LogPolicy
    if (-not $policy) { return $true } # Safety: emit everything if policy missing

    $modePolicy = $null
    if ($policy.PSObject.Properties.Match($Mode).Count -gt 0) {
        $modePolicy = $policy.$Mode
    } else {
        # Fallback to OBSERVATION_ONLY if mode not explicitly defined
        $modePolicy = $policy.OBSERVATION_ONLY
    }

    if (-not $modePolicy) { return $true }

    # Check explicit suppression
    if ($modePolicy.suppress -and ($ResultCode -in $modePolicy.suppress)) {
        return $false
    }

    # Check explicit whitelist
    if ($modePolicy.always_emit -and ($ResultCode -in $modePolicy.always_emit)) {
        return $true
    }

    # Return default for this mode
    return $modePolicy.emit_by_default
}

# Export for T08 (simple dot-source awareness)
$LogPolicyActive = $true
