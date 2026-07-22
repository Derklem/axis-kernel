<#
.SYNOPSIS
  Reality_Class.psm1
  Enforces L3.2 Reality Classification Schema.
#>

function New-RealityObject {
    param(
        [string]$Class,
        [string]$Source,
        [double]$Confidence = 1.0,
        [array]$Evidence = @()
    )

    $validClasses = @("L0_OBSERVED", "L1_INFERRED", "L2_SIMULATED", "L3_SYMBOLIC")
    if ($Class -notin $validClasses) { throw "Invalid Reality Class: $Class" }

    return [ordered]@{
        class             = $Class
        confidence        = $Confidence
        source_of_truth   = $Source
        evidence_refs     = $Evidence
        created_ts        = (Get-Date).ToUniversalTime().ToString("o")
        promotion_blocked = ($Class -in @("L2_SIMULATED", "L3_SYMBOLIC"))
    }
}

function Test-RealityExecutionAllowed {
    param($artifact)

    if (-not $artifact.reality) { 
        Write-Warning "[RealityGuard] Execution Blocked: Missing Reality Header"
        return $false 
    }

    if ($artifact.reality.class -ne "L0_OBSERVED") {
        Write-Warning "[RealityGuard] Execution Blocked: Non-L0 Class ($($artifact.reality.class))"
        return $false
    }

    if ($artifact.reality.confidence -lt 0.9) {
        Write-Warning "[RealityGuard] Execution Blocked: Low Confidence L0 ($($artifact.reality.confidence))"
        return $false
    }

    return $true
}

Export-ModuleMember -Function New-RealityObject, Test-RealityExecutionAllowed
