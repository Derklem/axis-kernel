<#
.SYNOPSIS
  T617_Lattice_Expander.ps1
  Semantically braids neural shards and living syntax into the Memory Lattice.
  Vector 1: Cognitive Indexing.
#>

$LedgerPath = "D:\Infinite\Infinity\Memory\indexes\Neural_Pulse_Ledger.jsonl"
$LatticePath = "D:\Infinite\Infinity\Memory\indexes\Memory_Lattice_Edges.jsonl"
$ResonancePath = "D:\Infinite\Infinity\Memory\indexes\Resonance_State.json"

Write-Host "[EXPANSION] Expanding Cognitive Lattice..." -ForegroundColor Cyan

# 1. Load Data
if (-not (Test-Path $LedgerPath)) { Write-Error "Neural Ledger missing."; exit 1 }
$shards = Get-Content $LedgerPath | ConvertFrom-Json

# 2. Braiding Logic (Cross-Linking Shards)
# We create 'RESONANCE_EDGE' links between shards to establish semantic structure.
$edges = @()
for ($i = 0; $i -lt $shards.Count; $i++) {
    for ($j = $i + 1; $j -lt $shards.Count; $j++) {
        $source = $shards[$i]
        $target = $shards[$j]
        
        # Heuristic: Link if both are shards or if they share a source
        if ($source.kind -eq $target.kind -or $source.metadata.source -eq $target.metadata.source) {
            $edge = [ordered]@{
                pk        = "EDGE-" + [Guid]::NewGuid().ToString().Substring(0, 8)
                ts_utc    = [DateTime]::UtcNow.ToString("o")
                source_pk = $source.pk
                target_pk = $target.pk
                kind      = "BRAID_INT INTEGRATION"
                weight    = 1.0
                metadata  = @{
                    vector = "Vector-1:Cognitive-Indexing"
                    type   = "Semantic_Resonance"
                }
            }
            $edges += $edge
        }
    }
}

# 3. Commit Edges
if ($edges.Count -gt 0) {
    $edges | ConvertTo-Json -Compress | Add-Content $LatticePath
    Write-Host "[EXPANSION] Braided $($edges.Count) semantic edges." -ForegroundColor Green
}
else {
    Write-Warning "[EXPANSION] No new edges identified."
}

# 4. Trigger Resonance Update
& "D:\Infinite\Infinity\Truth_Engine\T26_Coherence_Monitor.ps1"

Write-Host "[EXPANSION] Lattice Expansion Complete." -ForegroundColor Magenta
