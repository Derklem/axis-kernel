# Axis_Compute_StateVector.ps1
# Phase 47: Manifest-driven aggregation of cryptographic state.

$ErrorActionPreference = "Stop"

$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$TruthDir = Join-Path $Root "Truth_Engine"
$ManifestFile = Join-Path $GovDir "state_vector_manifest.json"

if (-not (Test-Path $ManifestFile)) {
    Write-Error "State vector manifest not found: $ManifestFile"
    exit 1
}

$manifest = Get-Content $ManifestFile | ConvertFrom-Json

# Import helpers (T17 for Get-LedgerHeadHash)
Import-Module (Join-Path $TruthDir "T17_MemoryIndexer.psm1") -Force

function Compute-FileHash-Simple($path) {
    if (-not (Test-Path $path)) { return "null" }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $stream = [System.IO.File]::OpenRead($path)
        $hash = [BitConverter]::ToString($sha.ComputeHash($stream)) -replace "-", ""
        $stream.Close()
        return "sha256:" + $hash.ToLower()
    }
    finally { $sha.Dispose() }
}

$vector = [ordered]@{
    ts_utc = (Get-Date).ToUniversalTime().ToString("o")
}

foreach ($entry in $manifest.components.PSObject.Properties) {
    $name = $entry.Name
    $c = $entry.Value
    $fullPath = Join-Path $Root $c.path
    
    if ($c.kind -eq "ledger_head") {
        $head = Get-LedgerHeadHash $fullPath
        $vector[$name] = if ($head) { $head.LastEventHash } else { "null" }
    }
    elseif ($c.kind -eq "file_sha256") {
        $vector[$name] = Compute-FileHash-Simple $fullPath
    }
}

# Output as JSON for consumption
$vector | ConvertTo-Json
