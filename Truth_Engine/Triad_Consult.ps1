<# 
.SYNOPSIS
    Triad Consult Interface
.DESCRIPTION
    Read-only service for Mind/Earth/Shadow to query the Truth Engine.
    Returns a grounding summary for a given ClaimId or ClaimText.
#>

param(
    [string]$RootPath = "D:\Infinite\Infinity\Truth_Engine",
    [string]$ClaimId,
    [string]$ClaimText
)

$ClaimsPath = Join-Path $RootPath "Content\TE_Claims_Index.jsonl"
$GroundingPath = Join-Path $RootPath "Content\TE_Grounding_Ledger.jsonl"

if (-not (Test-Path $ClaimsPath) -or -not (Test-Path $GroundingPath)) {
    return [PSCustomObject]@{ error = "Truth Engine data missing or not yet grounded." }
}

# 1. Load Data
$claims = @(Get-Content $ClaimsPath | ForEach-Object { if ($_) { $_ | ConvertFrom-Json } } | Where-Object { $null -ne $_ })
$ledger = @(Get-Content $GroundingPath | ForEach-Object { if ($_) { $_ | ConvertFrom-Json } } | Where-Object { $null -ne $_ })

function Get-ClaimSignature {
    param([string]$text)
    if ([string]::IsNullOrWhiteSpace($text)) { return "empty" }
    $clean = $text.ToLower() -replace '[^a-z0-9 ]', ''
    $tokens = @($clean.Split(" `t`n`r", [System.StringSplitOptions]::RemoveEmptyEntries) | Select-Object -Unique | Sort-Object)
    return ($tokens -join " ")
}

# 2. Find Claim
$claim = $null
if ($ClaimId) {
    Write-Host "[DEBUG-TRIAD] Looking for ClaimId: $ClaimId" -ForegroundColor Gray
    $claim = $claims | Where-Object { $_.claim_id -eq $ClaimId } | Select-Object -First 1
    if ($null -eq $claim) { Write-Host "[DEBUG-TRIAD] ClaimId $ClaimId not found in $($claims.Count) claims." -ForegroundColor Yellow }
}
elseif ($ClaimText) {
    $sig = Get-ClaimSignature -text $ClaimText
    $claim = $claims | Where-Object { (Get-ClaimSignature -text $_.canonical_text) -eq $sig } | Select-Object -First 1
}

if ($null -eq $claim) {
    return [PSCustomObject]@{ error = "Claim not found in Historical Lattice." }
}

# 3. Find Grounding Status
$grounding = $ledger | Where-Object { $_.claim_id -eq $claim.claim_id } | Select-Object -First 1

if ($null -eq $grounding) {
    return [PSCustomObject]@{ error = "Claim found but not yet processed by Grounding Layer (T05)." }
}

# 4. Construct Response
$response = [PSCustomObject]@{
    claim_id          = $claim.claim_id
    canonical_text    = $claim.canonical_text
    epistemic_status  = $grounding.epistemic_status
    status_confidence = $grounding.status_confidence
    status_reason     = $grounding.status_reason
    support           = $claim.support
    notes             = New-Object System.Collections.Generic.List[string]
}

# Add automated notes
if ($grounding.source_roles.primary_present) { [void]$response.notes.Add("Claim appears in PRIMARY bucket.") }
if ($grounding.source_roles.growth_present) { [void]$response.notes.Add("Claim is being amplified/contextualized in GROWTH bucket.") }
if ($grounding.source_roles.ignore_dominant) { [void]$response.notes.Add("Echo pattern detected: IGNORE bucket dominates primary/growth signals.") }
if ($grounding.epistemic_status -eq "TENUOUS") { [void]$response.notes.Add("Low observational density; grounding may shift with more data.") }

return $response
