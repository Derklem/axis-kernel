<#
.SYNOPSIS
    Axis Egress Gate (T18)
.DESCRIPTION
    Validates intents before they reach external platforms.
    Enforces 'Fail-Closed' status and 'Constitutional Freeze' targets.
#>

function Invoke-EgressValidation {
    param(
        [Parameter(Mandatory=$true)][pscustomobject]$Intent,
        [Parameter(Mandatory=$true)][pscustomobject]$SystemMode,
        [Parameter(Mandatory=$true)][string]$ConstraintsPath
    )

    $decision = @{
        ts = (Get-Date).ToUniversalTime().ToString("o")
        intent_id = $Intent.intent_id
        target = $Intent.target
        allowed = $false
        reason = "BLOCK_DEFAULT"
    }

    # 1. Platform Awareness
    $platform = "UNKNOWN"
    if ($Intent.target -is [string]) {
        if ($Intent.target -match "moltbook:") { $platform = "MOLTBOOK" }
    } elseif ($Intent.target -is [pscustomobject] -and $Intent.target.platform) {
        $platform = $Intent.target.platform.ToUpper()
    }

    # 2. Hard Fail-Closed check
    if ($SystemMode.mode -eq "OBSERVATION_ONLY") {
        $decision.reason = "MODE_OBSERVE_ONLY"
        return $decision
    }

    # 3. Constitutional Freeze Check
    if (Test-Path $ConstraintsPath) {
        try {
            $cc = Get-Content $ConstraintsPath -Raw | ConvertFrom-Json
            foreach ($ac in $cc.active_constraints) {
                if ($ac.id -eq "SOVEREIGN_FREEZE_01") {
                    # Freeze is active. Check targets.
                    $frozen = $ac.targets # Expecting array or '*'
                    if ($frozen -eq "*" -or ($frozen -contains $platform) -or ($frozen -contains "EGRESS")) {
                        $decision.reason = "CONSTITUTIONAL_FREEZE_ACTIVE ($platform)"
                        return $decision
                    }
                }
            }
        } catch {
            $decision.reason = "CONSTRAINTS_PARSE_FAILURE"
            return $decision
        }
    }

    # 4. Default Allow (if not blocked by above)
    $decision.allowed = $true
    $decision.reason = "EGRESS_ALLOWED"
    return $decision
}
