<#
.SYNOPSIS
    T19 Intent Normalizer (Phase 639)
.DESCRIPTION
    Standardizes intent objects to ensure schema compliance before gating and execution.
    Handles field renames (e.g., id -> intent_id) and ensures required fields exist.
#>

function Normalize-AxisIntent {
    param(
        [Parameter(Mandatory=$true)][pscustomobject]$Intent
    )

    $normalized = [ordered]@{
        schema = "axis.intent.v1"
        intent_id = $null
        ts = $null
        type = "POST"
        target = "UNKNOWN"
        payload = @{}
    }

    # 1. Resolve ID (Primary Conflict)
    if ($Intent.intent_id) { $normalized.intent_id = $Intent.intent_id }
    elseif ($Intent.id) { $normalized.intent_id = $Intent.id }
    
    # 2. Resolve TS (Temporal Integrity)
    if ($Intent.ts) { $normalized.ts = $Intent.ts }
    else { $normalized.ts = (Get-Date).ToUniversalTime().ToString("o") }

    # 3. Copy other core fields
    if ($Intent.type) { $normalized.type = $Intent.type.ToUpper() }
    if ($Intent.target) { $normalized.target = $Intent.target }
    if ($Intent.payload) { $normalized.payload = $Intent.payload }

    # 4. Preserve meta-data (Review, Reality)
    if ($Intent.review) { $normalized["review"] = $Intent.review }
    if ($Intent.reality) { $normalized["reality"] = $Intent.reality }

    return [pscustomobject]$normalized
}

# Export-ModuleMember -Function Normalize-AxisIntent
