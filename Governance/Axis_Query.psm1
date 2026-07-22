
# Axis_Query.psm1
# Unified Retrieval Interface for Axis T17 Truth.
# Routes queries to Hot (Daily Segments) or Warm (Monthly Packs) storage.

param(
    [string]$MemoryRoot = "D:\Infinite\Infinity\Memory"
)

$LedgerDir = Join-Path $MemoryRoot "ledger"
$PackDir = Join-Path $MemoryRoot "packs"
$ManifestFile = Join-Path $PackDir "compaction_manifest.jsonl"

# --- CACHE ---
# In a real system, we'd cache the manifest in memory.
# For now, we read it on demand.

function Get-AxisEvent {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory=$true, ValueFromPipeline=$true)]
        [string]$Id
    )

    # 1. Check Hot Segments (Last 30 days usually, here just all in LedgerDir)
    # Optimization: If we had a hot index, use it. For now, grep.
    # Actually, T17 indexer keeps `seen_keys` indexes in `Memory\indexes\seen_{ledger}.jsonl`
    # We can check those first if we know the ledger.
    # But ID might not imply ledger.
    
    # Simple strategy:
    # A. Search Hot Segments (Text Search / Index)
    # B. Search Packs (Text Search / Manifest)

    # A. Hot Search
    $hotFiles = Get-ChildItem $LedgerDir -Filter "*_segment.jsonl"
    foreach ($file in $hotFiles) {
        # Fast scan?
        if (Select-String -Path $file.FullName -Pattern $Id -SimpleMatch -Quiet) {
            $line = Select-String -Path $file.FullName -Pattern $Id -SimpleMatch | Select-Object -First 1
            if ($line) {
                return ($line.Line | ConvertFrom-Json)
            }
        }
    }

    # B. Warm Search (Index Priority)
    if (Test-Path $PackDir) {
        # 1. Check Indexes
        # Optimization: We could keep indexes in memory if small, or grep them (smaller surface).
        $indexes = Get-ChildItem $PackDir -Filter "*_pack.index.jsonl"
        foreach ($idxFile in $indexes) {
            # Use Select-String on the INDEX file (much smaller)
            $match = Select-String -Path $idxFile.FullName -Pattern $Id -SimpleMatch | Select-Object -First 1
            if ($match) {
                # Found in index!
                try {
                    $entry = $match.Line | ConvertFrom-Json
                    $packFile = Join-Path $PackDir $entry.pack
                    if (Test-Path $packFile) {
                        # Direct Read (1-indexed line number from Select-String/Index)
                        # Get-Content -TotalCount is slow for deep lines, but better than scanning.
                        # DotNet stream skip is best.
                        $lines = Get-Content $packFile -TotalCount $entry.line | Select-Object -Last 1
                        return ($lines | ConvertFrom-Json)
                    }
                } catch {
                    Write-Warning "Index hit failed to resolve: $_"
                }
            }
        }

        # 2. Fallback: Scan Packs (Slow)
        # Only if index missing or corrupted
        $packs = Get-ChildItem $PackDir -Filter "*_pack.jsonl"
        foreach ($pack in $packs) {
            if (Select-String -Path $pack.FullName -Pattern $Id -SimpleMatch -Quiet) {
                $line = Select-String -Path $pack.FullName -Pattern $Id -SimpleMatch | Select-Object -First 1
                if ($line) {
                    return ($line.Line | ConvertFrom-Json)
                }
            }
        }
    }

    Write-Warning "Event $Id not found in T17 Memory."
    return $null
}

function Get-AxisEvents {
    [CmdletBinding()]
    param(
        [DateTime]$After,
        [DateTime]$Before,
        [string]$Ledger # Optional filter
    )
    
    # 1. Strategy: 
    # If $After is old, start with Packs.
    # If $After is recent, start with Hot.
    
    $results = @()
    
    # Todo: Implement time-range scanning based on filenames.
    # Pack names: yyyy-MM_pack.jsonl
    # Segment names: yyyy-MM-dd_segment.jsonl
    
    # NOT IMPLEMENTED FULLY IN MVP
    Write-Warning "Time-range query not fully implemented."
    return $results
}

Export-ModuleMember -Function Get-AxisEvent, Get-AxisEvents
