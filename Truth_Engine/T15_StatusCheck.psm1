# T15_StatusCheck.psm1
# v0.1 - Truth Engine Integration
# Connects Execution Layer (T08) to Epistemic Status (Status Ladder).

$TruthServicePath = "D:\Infinite\Infinity\Truth_Engine\Axis_Truth_Service.ps1"

function Get-ClaimStatus {
    <#
    .SYNOPSIS
        Queries the Truth Engine for the epistemic status of a claim.
    .DESCRIPTION
        Wraps Axis_Truth_Service to provide a structured status object.
        Returns $null if service is unavailable.
    .EXAMPLE
        $status = Get-ClaimStatus -ClaimId "CLM-123"
        if ($status.epistemic_status -eq "TENUOUS") { ... }
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$ClaimId,
        
        [string]$Caller = "T08_Executor"
    )

    if (-not (Test-Path $TruthServicePath)) {
        Write-Warning "T15: Truth Service not found at $TruthServicePath"
        return $null
    }

    try {
        # Invoke the service script
        # Returns object with: claim_id, epistemic_status, status_confidence, etc.
        $result = & $TruthServicePath -Action "CONSULT" -ClaimId $ClaimId -Caller $Caller
        
        if ($result.error) {
            Write-Warning "T15: Truth Service Error: $($result.error)"
            return $null
        }
        
        return $result
    }
    catch {
        Write-Warning "T15: Exception calling Truth Service: $_"
        return $null
    }
}

Export-ModuleMember -Function Get-ClaimStatus
