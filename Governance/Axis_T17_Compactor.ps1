
# Axis_T17_Compactor.ps1
# Phase 48: Compacts daily T17 memory segments into immutable monthly packs.

param(
    [string]$Root = "D:\Infinite\Infinity",
    [switch]$DryRun,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$MemoryRoot = Join-Path $Root "Memory"
$LedgerDir = Join-Path $MemoryRoot "ledger"
$PackDir = Join-Path $MemoryRoot "packs"
$ManifestPath = Join-Path $PackDir "compaction_manifest.jsonl"

function Get-Sha256($p) {
    if (-not (Test-Path $p)) { return $null }
    $s = [System.Security.Cryptography.SHA256]::Create()
    $b = [System.IO.File]::ReadAllBytes($p)
    $h = [BitConverter]::ToString($s.ComputeHash($b)).Replace("-", "").ToLower()
    $s.Dispose()
    return $h
}

# Ensure Pack Dir

# Ensure Pack Dir
if (-not (Test-Path $PackDir)) { New-Item -ItemType Directory -Path $PackDir -Force | Out-Null }

Write-Host "--- AXIS T17 COMPACTOR ---" -ForegroundColor Cyan

try {
    # 1. Identify Candidates (Older than current month)
    Write-Host "Step 1: Debug: Starting candidate identification..."
    $currentMonth = (Get-Date).ToString("yyyy-MM")
    $segments = Get-ChildItem -Path $LedgerDir -Filter "*_segment.jsonl" | Sort-Object Name
    
    # Group by Month
    $groups = @{}
    Write-Host "Grouping segments..."
    foreach ($file in $segments) {
        if ($file.Name -match "^(\d{4}-\d{2})-\d{2}_segment\.jsonl$") {
            $month = $matches[1]
            if ($month -lt $currentMonth) {
                if (-not $groups.ContainsKey($month)) { 
                    $groups[$month] = [System.Collections.ArrayList]::new() 
                }
                [void]$groups[$month].Add($file)
            }
        }
    }
    
    if ($groups.Count -eq 0) {
        Write-Host "No historical segments found to compact." -ForegroundColor Gray
        exit 0
    }
    
    Write-Host "Found $($groups.Count) months to compact."
    
    # 2. Process Groups (Sorted)
    $sortedMonths = $groups.Keys | Sort-Object
    foreach ($month in $sortedMonths) {
        $files = $groups[$month]
        $packFile = Join-Path $PackDir "${month}_pack.jsonl"
        $indexFile = Join-Path $PackDir "${month}_pack.index.jsonl"
        
        Write-Host "Processing $month ($($files.Count) segments) -> $packFile" -ForegroundColor Yellow
        
        if (Test-Path $packFile) {
            Write-Warning "  Pack already exists. Skipping (Re-compaction require manual clean currently)."
            continue
        }
    
        if ($DryRun) {
            Write-Host "  [DryRun] Would merge $($files.Count) files."
            continue
        }
    
        $manifestEntries = @()
        
        $packStream = [System.IO.StreamWriter]::new($packFile)
        $indexStream = [System.IO.StreamWriter]::new($indexFile)
        # Use Newline for consistent CRLF
        $packStream.NewLine = "`r`n"
        $indexStream.NewLine = "`r`n"
        
        $currentLine = 1
        
        try {
            foreach ($f in $files) {
                $lines = [System.IO.File]::ReadAllLines($f.FullName)
                if ($lines.Count -eq 0) { continue }
                
                # Calculate source hash for manifest
                $sha = [System.Security.Cryptography.SHA256]::Create()
                $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
                $hash = [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace("-", "").ToLower()
                $sha.Dispose()
        
                foreach ($line in $lines) {
                    $packStream.WriteLine($line)
                    
                    # Multi-Key Indexing (Simplified & Streaming)
                    if ($line -match '"event_id"\s*:\s*"([^"]+)"') {
                         $idxEntry = @{ k=$matches[1]; kind="event_id"; line=$currentLine; pack="${month}_pack.jsonl" }
                         $indexStream.WriteLine(($idxEntry | ConvertTo-Json -Compress))
                    }
                    if ($line -match '"audit_event_id"\s*:\s*"([^"]+)"') {
                         $idxEntry = @{ k=$matches[1]; kind="audit_event_id"; line=$currentLine; pack="${month}_pack.jsonl" }
                         $indexStream.WriteLine(($idxEntry | ConvertTo-Json -Compress))
                    }
                    if ($line -match '"hash"\s*:\s*"([^"]+)"') {
                         $idxEntry = @{ k=$matches[1]; kind="hash"; line=$currentLine; pack="${month}_pack.jsonl" }
                         $indexStream.WriteLine(($idxEntry | ConvertTo-Json -Compress))
                    }
                    if ($line -match '"corr_id"\s*:\s*"([^"]+)"') {
                         $idxEntry = @{ k=$matches[1]; kind="corr_id"; line=$currentLine; pack="${month}_pack.jsonl" }
                         $indexStream.WriteLine(($idxEntry | ConvertTo-Json -Compress))
                    }
                    
                    $currentLine++
                }
                
                $entry = @{
                    original_segment = $f.Name
                    pack_file = "${month}_pack.jsonl"
                    original_hash = $hash
                    event_count = $lines.Count
                    compacted_at = (Get-Date).ToString("o")
                    pack_is_derivative = $true
                    normalization = "CRLF"
                }
                $manifestEntries += $entry
            }
        }
        finally {
            $packStream.Close()
            $indexStream.Close()
            $packStream.Dispose()
            $indexStream.Dispose()
        }
        
        $packHash = Get-Sha256 $packFile
        $indexHash = Get-Sha256 $indexFile

        # Verify Creation & Update Manifest
        if (Test-Path $packFile) {
            Write-Host "  [OK] Pack and Index created." -ForegroundColor Green
            Write-Host "       Pack Hash:  $packHash" -ForegroundColor DarkGray
            Write-Host "       Index Hash: $indexHash" -ForegroundColor DarkGray
            
            # Update Manifest with Integrity Data
            foreach ($entry in $manifestEntries) {
                $entry["pack_sha256"] = $packHash
                $entry["index_sha256"] = $indexHash
                $entry["pack_line_count"] = $currentLine - 1
                
                $json = $entry | ConvertTo-Json -Compress
                [System.IO.File]::AppendAllLines($ManifestPath, [string[]]@($json))
            }
    
            # Cleanup/Archive Originals
            $ArchiveDir = Join-Path $LedgerDir "Archived_Segments"
            if (-not (Test-Path $ArchiveDir)) { New-Item -ItemType Directory -Path $ArchiveDir -Force | Out-Null }
            
            foreach ($f in $files) {
                Move-Item $f.FullName $ArchiveDir -Force
            }
            Write-Host "  [OK] Archived $($files.Count) segments." -ForegroundColor Gray
        }
    }
} catch {
    Write-Host "CRITICAL ERROR at line $($_.InvocationInfo.ScriptLineNumber): $($_.Exception.ToString())" -ForegroundColor Red
    exit 1
}
