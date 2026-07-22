# Axis_Provenance.psm1
# Phase 52: Provenance Explorer & Truth Forensics

$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$MemoryDir = Join-Path $Root "Memory"
$PackDir = Join-Path $MemoryDir "packs"
$EconModule = Join-Path $GovDir "Economics\Axis_IntegrityEconomics.psm1"
$PolicyPath = Join-Path $GovDir "Economics\econ_policy.json"

# Import Economics if available
if (Test-Path $EconModule) {
    # Import-Module $EconModule -ErrorAction SilentlyContinue
}

# --- Helpers ---

function Get-AxisSafeTail {
    param($path, $count)
    if (-not (Test-Path $path)) { return @() }
    $content = Get-Content $path -Tail $count -ErrorAction SilentlyContinue 
    if (-not $content) { return @() }
    return $content | ForEach-Object { try { $_ | ConvertFrom-Json } catch { } }
}

function Get-EconhardCap {
    if (Test-Path $PolicyPath) {
        $p = Get-Content $PolicyPath -Raw | ConvertFrom-Json
        return $p.throttle.hard_cap_at_pct
    }
    return 1.25 # Default
}

# --- Public Functions ---

function Estimate-Cost {
    param([string]$Key)
    return 15.0 # ICU
}

function Check-EconBudget {
    param([double]$Cost)
    
    if (Get-Command Get-EconStatus -ErrorAction SilentlyContinue) {
        $status = Get-EconStatus
        
        # 1. Fail Fast if already at Hard Cap
        if ($status.status -eq "HARD_CAP") {
            return @{ allowed=$false; reason="Daily budget HARD CAP reached." }
        }
        
        # 2. Predictive Check
        $hardCapPct = Get-EconhardCap
        $budget = $status.daily_budget
        if ($budget -gt 0) {
            $projected = $status.daily_spent + $Cost
            $limit = $budget * $hardCapPct
            if ($projected -gt $limit) {
                return @{ allowed=$false; reason="Operation would exceed Hard Cap limit ($($limit) ICU)." }
            }
        }
        
        return @{ allowed=$true; status=$status.status }
    }
    
    return @{ allowed=$true; reason="Econ module invalid" }
}

function Get-ProvenanceTrail {
    param([string]$Key)
    
    if ([string]::IsNullOrWhiteSpace($Key)) { return @() }
    
    $results = @()
    
    # 1. Hot Segments (Bounded: Last 20 files, max 50 hits total)
    $hotSegments = Get-ChildItem (Join-Path $MemoryDir "ledger") -Filter "*_segment.jsonl" | Sort-Object Name -Descending | Select-Object -First 20
    $hotHits = 0
    foreach ($seg in $hotSegments) {
        if ($hotHits -ge 50) { break }
        $matches = Select-String -Path $seg.FullName -Pattern $Key -SimpleMatch -List:$false
        foreach ($m in $matches) {
            try {
                $rec = $m.Line | ConvertFrom-Json
                $results += @{
                    ts_utc = if ($rec.ts_utc) { $rec.ts_utc } else { $rec.timestamp }
                    source = "HOT: $($seg.Name)"
                    record = $rec
                }
                $hotHits++
            } catch {}
        }
    }
    
    # 2. Warm Indexes (Strict Key Match)
    $indexes = Get-ChildItem $PackDir -Filter "*_pack.index.jsonl" | Sort-Object Name -Descending | Select-Object -First 50
    $useFastContains = ($Key.Length -ge 8)
    
    foreach ($idx in $indexes) {
        $reader = [System.IO.File]::OpenText($idx.FullName)
        try {
            while (($line = $reader.ReadLine()) -ne $null) {
                if ($useFastContains -and -not $line.Contains($Key)) { continue }
                
                try { $obj = $line | ConvertFrom-Json } catch { continue }
                
                # STRICT KEY MATCH REQUIRED for scan correctness
                if ($obj.k -ne $Key) { continue }
                
                # Fetch Logic (StreamReader Jump)
                $packName = $obj.pack
                $packPath = Join-Path $PackDir $packName
                if (Test-Path $packPath) {
                   $targetLine = [int]$obj.line
                   
                   $pReader = [System.IO.File]::OpenText($packPath)
                   try {
                       # Skip lines (0-based seek)
                       for ($i=1; $i -lt $targetLine; $i++) { [void]$pReader.ReadLine() }
                       $packLine = $pReader.ReadLine()
                       
                       if ($packLine) {
                           $rec = $packLine | ConvertFrom-Json
                           $results += @{
                               ts_utc = if ($rec.ts_utc) { $rec.ts_utc } else { $rec.timestamp }
                               source = "WARM: $packName"
                               record = $rec
                           }
                       }
                   } finally {
                       $pReader.Dispose()
                   }
                }
            }
        } finally {
            $reader.Dispose()
        }
    }
    
    # 3. Governance Ledgers (Pulse, Anchor)
    $govFiles = @("integrity_pulse_ledger.jsonl", "external_anchor_ledger.jsonl")
    foreach ($f in $govFiles) {
        $p = Join-Path $GovDir $f
        if (Test-Path $p) {
             $matches = Select-String -Path $p -Pattern $Key -SimpleMatch -List:$false
             foreach ($m in $matches) {
                try {
                    $rec = $m.Line | ConvertFrom-Json
                    $results += @{
                        ts_utc = if ($rec.ts_utc) { $rec.ts_utc } else { $rec.timestamp }
                        source = "GOV: $f"
                        record = $rec
                    }
                } catch {}
             }
        }
    }
    
    # Reliable Sort (Fallback for missing timestamps)
    # Reliable Sort (Fallback for missing timestamps)
    return $results | Sort-Object { 
        if ($_.ts_utc) { [DateTime]$_.ts_utc } 
        elseif ($_.record.timestamp) { [DateTime]$_.record.timestamp }
        else { [DateTime]::MinValue }
    }
}

# --- Private Helpers ---

function Is-Hash64([string]$s) {
    if ([string]::IsNullOrWhiteSpace($s)) { return $false }
    return ($s -match '^[0-9a-fA-F]{64}$')
}

function Get-ProvenanceGraph {
    param(
        [string]$Key,
        [string]$Mode = "Event", # Event, Claim, Coin
        [int]$MaxNodes = 50,
        [int]$MaxEdges = 100
    )
    
    $nodes = [ordered]@{}
    $edges = @()
    $queue = [System.Collections.Generic.Queue[string]]::new()
    $processed = [System.Collections.Generic.HashSet[string]]::new()
    
    if (-not [string]::IsNullOrWhiteSpace($Key)) {
        $queue.Enqueue($Key)
    }
    
    $expansions = 0
    $unresolvedEdges = 0
    $evidenceTruncated = 0
    $missingKeyHits = 0
    $partial = $false
    $partialReason = $null
    
    while ($queue.Count -gt 0 -and $nodes.Count -lt $MaxNodes) {
        $currentKey = $queue.Dequeue()
        if ($processed.Contains($currentKey)) { continue }
        $processed.Add($currentKey) | Out-Null
        
        # 1. Fetch Records
        $records = Get-ProvenanceTrail -Key $currentKey
        if ($records.Count -eq 0) { 
            $missingKeyHits++
            continue 
        }
        
        # 2. Process Records -> Nodes
        foreach ($r in $records) {
            $rec = $r.record
            
            # ID Resolution
            $id = $rec.hash
            if (-not $id) { $id = $rec.pulse_id }
            if (-not $id) { $id = $rec.event_id }
            if ($Mode -eq "Claim" -and $rec.claim_id) { $id = $rec.claim_id }
            if ($Mode -eq "Coin" -and $rec.coin_id) { $id = $rec.coin_id }
            if (-not $id) { continue }
            
            if (-not $nodes.Contains($id)) {
                if ($nodes.Count -ge $MaxNodes) {
                    $partial = $true
                    $partialReason = "Node limit reached ($MaxNodes)"
                    break
                }
                
                $nodes[$id] = @{
                    id = $id
                    kind = if ($rec.kind) { $rec.kind } elseif ($rec.action) { "action" } else { "event" }
                    ts = if ($r.ts_utc) { $r.ts_utc } else { $rec.timestamp }
                    source = $r.source
                    label = if ($rec.action) { $rec.action } elseif ($rec.status) { "$($rec.mode) $($rec.status)" } else { $rec.kind }
                    tier = if ($r.source -match "HOT") { "HOT" } elseif ($r.source -match "WARM") { "WARM" } else { "GOV" }
                    keys = @{
                        hash = $rec.hash
                        event_id = $rec.event_id
                        corr_id = $rec.corr_id
                        claim_id = $rec.claim_id
                        coin_id = $rec.coin_id
                    }
                }
                
                # 3. Queue Expansions (Edges)
                $expansions++ 
                
                # Mode-Specific Expansion Rules
                
                # EVENT MODE: Previous Hash Chain
                if ($Mode -eq "Event") {
                    $target = $rec.previous_hash
                    if ($target -and $target.Length -gt 10 -and $target -ne "GENESIS" -and $target -ne "00000000000000000000000000000000") {
                        if ($edges.Count -lt $MaxEdges) {
                            # Strict Hash Check for Events
                            if (Is-Hash64 $target) {
                                $edges += @{ from=$id; to=$target; type="previous_hash"; resolved=$true }
                                if (-not $processed.Contains($target)) { $queue.Enqueue($target) }
                            } else {
                                $edges += @{ from=$id; to=$target; type="previous_hash"; resolved=$false }
                                $unresolvedEdges++
                            }
                        }
                    }
                }
                
                # CLAIM MODE: Reasoning Chain & Evidence
                if ($Mode -eq "Claim") {
                    # Parent Claim
                    $target = $rec.parent_claim_id
                    if ($target) {
                         if ($edges.Count -lt $MaxEdges) {
                            # Assume Claims are resolvable if present
                            $edges += @{ from=$id; to=$target; type="parent_claim"; resolved=$true }
                            if (-not $processed.Contains($target)) { $queue.Enqueue($target) }
                         }
                    }
                    # Source Events (Evidence) - Bounded Fan-out
                    if ($rec.source_event_ids) {
                        $evidenceCount = 0
                        $MaxEvidence = 5
                        $totalEvidence = $rec.source_event_ids.Count
                        foreach ($eid in $rec.source_event_ids) {
                            if ($evidenceCount -ge $MaxEvidence) { 
                                $evidenceTruncated += ($totalEvidence - $evidenceCount)
                                break 
                            }
                            if ($edges.Count -lt $MaxEdges) {
                                if (Is-Hash64 $eid) {
                                    $edges += @{ from=$id; to=$eid; type="evidence"; resolved=$true }
                                    if (-not $processed.Contains($eid)) { $queue.Enqueue($eid) }
                                } else {
                                    $edges += @{ from=$id; to=$eid; type="evidence"; resolved=$false }
                                    $unresolvedEdges++
                                }
                                $evidenceCount++
                            }
                        }
                    }
                }
                
                # COIN MODE: Value Flow
                if ($Mode -eq "Coin") {
                    # Inputs (From)
                    $target = $rec.from_id
                    if ($target) {
                         if ($edges.Count -lt $MaxEdges) {
                            # If we had Is-CoinId or Is-AccountHash, we'd use it here.
                            # For now, simplistic check:
                            $edges += @{ from=$target; to=$id; type="transfer"; resolved=$true }
                            if (-not $processed.Contains($target)) { $queue.Enqueue($target) }
                         }
                    }
                }
            }
        }
        if ($partial) { break }
    }
    
    return @{
        ok = $true
        graph = @{
            nodes = $nodes.Values | Sort-Object ts
            edges = $edges
        }
        stats = @{
            nodeCount = $nodes.Count
            edgeCount = $edges.Count
            expansions = $expansions
            unresolvedEdges = $unresolvedEdges
            evidenceTruncated = $evidenceTruncated
            missingKeyHits = $missingKeyHits
            partial = $partial
            reason = $partialReason
            mode = $Mode
        }
    }
}

Export-ModuleMember -Function Get-ProvenanceTrail, Estimate-Cost, Check-EconBudget, Get-ProvenanceGraph
