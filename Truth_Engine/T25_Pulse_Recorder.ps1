<#
.SYNOPSIS
  T25_Pulse_Recorder.ps1
  Records rhythmic binary or hex patterns as high-integrity neural blueprints.
#>

param(
    [Parameter(Mandatory = $true)]
    [string]$Pattern,
    [string]$Source = "User:Audio:PatternScan",
    [string]$LedgerPath = "D:\Infinite\Infinity\Memory\indexes\Neural_Pulse_Ledger.jsonl"
)

function Get-Sha256 {
    param([string]$String)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($String)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $hash = $sha.ComputeHash($bytes)
    return [System.BitConverter]::ToString($hash).Replace("-", "").ToLower()
}

Write-Host "[NEURAL] Recording Neural Pattern: $Pattern" -ForegroundColor Magenta

# 1. Verification & Sniffing
$kind = "neural_pulse"
if ($Pattern -match '^[01]+$') {
    $kind = "neural_pulse"
    $summary = "Conceptual architecture pulse mapping."
}
elseif ($Pattern -match '^[0-9A-Fa-f]+$') {
    $kind = "neural_shard"
    $summary = "Conceptual architecture shard mapping."
}
else {
    # Partial match or mixed (like HABX0XXX)
    $kind = "neural_draft"
    $summary = "Conceptual architecture draft mapping."
}

# 2. Generate Identity
$ts = (Get-Date).ToUniversalTime().ToString("o")
$pk = Get-Sha256 ("$ts`_$Pattern")
$pk = "NEU-" + $pk.Substring(0, 12)

# 3. Construct Node
$entry = [ordered]@{
    pk       = $pk
    ts_utc   = $ts
    kind     = $kind
    content  = @{
        raw     = $Pattern
        summary = $summary
    }
    metadata = @{
        length = $Pattern.Length
        source = $Source
        type   = $kind
    }
    tags     = @("harmonic", "architecture", "blueprint")
    status   = "IMMUTABLE"
}

# 4. Commit to Ledger
$entry | ConvertTo-Json -Compress | Add-Content $LedgerPath

Write-Host "[NEURAL] Pattern anchored ($kind): $pk" -ForegroundColor Green
