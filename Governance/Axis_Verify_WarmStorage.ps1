# Axis_Verify_WarmStorage.ps1
# Phase 49 Hardening: Verifies integrity of Warm Storage (Packs & Indexes) against Manifest.

param(
    [string]$Root = "D:\Infinite\Infinity",
    [switch]$LatestOnly
)

$ErrorActionPreference = "Stop"

$MemoryRoot = Join-Path $Root "Memory"
$PackDir = Join-Path $MemoryRoot "packs"
$ManifestPath = Join-Path $PackDir "compaction_manifest.jsonl"

Write-Output "--- AXIS WARM STORAGE VERIFIER ---"

if (-not (Test-Path $ManifestPath)) {
    Write-Warning "Compaction Manifest not found at $ManifestPath. Skipping check."
    exit 0
}

# Read Manifest
$entries = @()
try {
    $lines = Get-Content $ManifestPath
    foreach ($line in $lines) {
        if (-not [string]::IsNullOrWhiteSpace($line)) {
            $entries += ($line | ConvertFrom-Json)
        }
    }
} catch {
    Write-Error "Failed to parse Compaction Manifest: $_"
    exit 1
}

if ($entries.Count -eq 0) {
    Write-Warning "Manifest empty."
    exit 0
}

# Dedup Logic: Manifest has one entry per original segment, pointing to the same pack.
# We only need to verify each unique pack once.
$uniquePacks = $entries | Group-Object pack_file

if ($LatestOnly) {
    # Sort by compaction time or pack name to find latest
    $latest = $uniquePacks | Sort-Object Name | Select-Object -Last 1
    $uniquePacks = @($latest)
    Write-Host "Mode: LatestOnly (Verifying 1 Pack)" -ForegroundColor Yellow
} else {
    Write-Host "Mode: Full (Verifying $($uniquePacks.Count) Packs)" -ForegroundColor Cyan
}

$fails = 0

function Check-Hash($path, $expected) {
    if (-not (Test-Path $path)) { return "MISSING" }
    $s = [System.Security.Cryptography.SHA256]::Create()
    $b = [System.IO.File]::ReadAllBytes($path)
    $h = [BitConverter]::ToString($s.ComputeHash($b)).Replace("-", "").ToLower()
    $s.Dispose()
    
    if ($h -eq $expected) { return "MATCH" }
    return "MISMATCH (Exp: $expected, Got: $h)"
}

foreach ($group in $uniquePacks) {
    $packName = $group.Name
    # Get metadata from the first entry in group (all share same pack/index metadata)
    $meta = $group.Group[0]
    
    $packPath = Join-Path $PackDir $packName
    $indexName = $packName.Replace(".jsonl", ".index.jsonl")
    $indexPath = Join-Path $PackDir $indexName
    
    Write-Host "Verifying $packName..." -NoNewline
    
    # 1. Verify Pack Hash
    if ($meta.pack_sha256) {
        $res = Check-Hash $packPath $meta.pack_sha256
        if ($res -ne "MATCH") {
            Write-Host " [PACK FAIL: $res]" -ForegroundColor Red
            $fails++
        } else {
            Write-Host " [PACK OK]" -ForegroundColor Green -NoNewline
        }
    } else {
        Write-Host " [PACK SKIP (No Hash)]" -ForegroundColor DarkGray -NoNewline
    }
    
    # 2. Verify Index Hash
    if ($meta.index_sha256) {
        $res = Check-Hash $indexPath $meta.index_sha256
        if ($res -ne "MATCH") {
            Write-Host " [INDEX FAIL: $res]" -ForegroundColor Red
            $fails++
        } else {
            Write-Host " [INDEX OK]" -ForegroundColor Green -NoNewline
        }
    } else {
         # Try to infer index existence?
         if (Test-Path $indexPath) {
             Write-Host " [INDEX UNVERIFIED]" -ForegroundColor Yellow -NoNewline
         }
    }
    
    Write-Host ""
}

if ($fails -eq 0) {
    Write-Host "WARM STORAGE INTEGRITY VERIFIED." -ForegroundColor Green
    exit 0
} else {
    Write-Error "WARM STORAGE INTEGRITY FAILED ($fails errors)."
    exit 1
}
