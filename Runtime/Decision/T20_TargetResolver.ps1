<#
.SYNOPSIS
    T20 Target Resolver (Phase 640)
.DESCRIPTION
    Standardizes intent targets into a canonical URI format.
    Ensures Egress Gate and Auth Sentinel use a consistent identifier.
#>

function Resolve-AxisTarget {
    param(
        [Parameter(Mandatory=$true)][pscustomobject]$Intent
    )

    $targetInput = $Intent.target
    $uri = "UNKNOWN"

    if ($targetInput -is [string]) {
        # Already a string, ensure it has a scheme
        if ($targetInput -match ":") {
            $uri = $targetInput
        } else {
            # Default to moltbook if no scheme and looks like submolt
            $uri = "moltbook:$targetInput"
        }
    } elseif ($targetInput -is [hashtable] -or $targetInput -is [pscustomobject]) {
        $platform = if ($targetInput.platform) { $targetInput.platform } else { "UNKNOWN" }
        $sub = if ($targetInput.submolt) { $targetInput.submolt } elseif ($targetInput.target) { $targetInput.target } else { "general" }
        $uri = "$($platform):$($sub)"
    }

    # Normalize case
    $uri = $uri.ToLower().Trim()

    return $uri
}

# Export-ModuleMember -Function Resolve-AxisTarget
