<#
.SYNOPSIS
  T18_EvidenceGraph.ps1 (Module L3.3 - Simple)
#>

param(
    [string]$Action = "COMPILE"
)

# Configuration
$EpistemicDir = "D:\Infinite\Infinity\Runtime\Epistemic"
$MoltbookDir = "D:\Infinite\Infinity\Runtime\Moltbook"
$StateFile = Join-Path $EpistemicDir "Evidence_Graph_State.json"
$L0NodesFile = Join-Path $EpistemicDir "Evidence_Graph_Nodes_L0.jsonl"
$L1NodesFile = Join-Path $EpistemicDir "Evidence_Graph_Nodes_L1.jsonl"
$EdgesFile = Join-Path $EpistemicDir "Evidence_Graph_Edges.jsonl"
$ReportFile = Join-Path $EpistemicDir "Evidence_Graph_Report.json"

$RunLog = Join-Path $MoltbookDir "run_log.jsonl"

function Get-NodeID ($str) {
    if (-not $str) { return "null" }
    $algo = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($str)
    $hash = [BitConverter]::ToString($algo.ComputeHash($bytes)).Replace("-", "").ToLower().Substring(0, 16)
    return $hash
}

function Save-State ($s) {
    $s | ConvertTo-Json -Depth 5 | Set-Content $StateFile -Encoding UTF8
}

function Get-State {
    if (Test-Path $StateFile) { return (Get-Content $StateFile -Raw | ConvertFrom-Json) }
    return @{ cursors = @{ run_log = 0 }; last_compile_ts = "1970-01-01" }
}

function Ingest-L0 ($state) {
    Write-Host "[Compiler] Ingesting L0..." -ForegroundColor Cyan
    
    if (-not (Test-Path $RunLog)) { return $state }
    
    $lines = Get-Content $RunLog
    $start = $state.cursors.run_log
    if ($start -ge $lines.Count) { return $state }
    
    $newLines = $lines | Select-Object -Skip $start
    $processed = 0
    
    foreach ($line in $newLines) {
        $processed++
        try {
            $evt = $line | ConvertFrom-Json
            
            $isL0 = $false
            if ($evt.event_type -eq "status_result") { $isL0 = $true }
            if ($evt.event_type -eq "verified_post") { $isL0 = $true }
            if ($evt.reality) { 
                if ($evt.reality.class -eq "L0_OBSERVED") { $isL0 = $true } 
            }
            
            if ($isL0) {
                $idStr = "$($evt.ts)$($evt.event_type)$($evt.run_id)"
                $nodeId = Get-NodeID $idStr
                
                $dJson = ""
                try { $dJson = $evt.details | ConvertTo-Json -Compress -Depth 1 } catch { $dJson = "error" }

                $node = @{
                    id           = $nodeId
                    type         = "L0_NODE"
                    l0_type      = "EVIDENCE"
                    ts           = $evt.ts
                    source       = "run_log"
                    raw_data_ref = $evt.run_id
                    desc         = "$($evt.event_type): $dJson"
                    node_version = 1
                }
                
                $node | ConvertTo-Json -Compress | Add-Content $L0NodesFile -Encoding UTF8
                $state.stats.L0_nodes++
            }
        }
        catch {}
    }
    
    $state.cursors.run_log += $processed
    return $state
}

function Ingest-L1 ($state) {
    Write-Host "[Compiler] Ingesting L1..." -ForegroundColor Cyan
    
    # Auth State
    $authFile = Join-Path $MoltbookDir "auth_state.json"
    if (Test-Path $authFile) {
        try {
            $auth = Get-Content $authFile -Raw | ConvertFrom-Json
            $idStr = "AUTH_STATE_SNAPSHOT$($auth.updated_ts)"
            $nodeId = Get-NodeID $idStr
            
            $node = @{
                id            = $nodeId
                type          = "L1_NODE"
                l1_type       = "CONCLUSION"
                subject       = "AUTH_STATE"
                score         = $auth.auth_state
                ts            = (Get-Date).ToUniversalTime().ToString("o")
                evidence_refs = $auth.proof.evidence_refs
                source_file   = "auth_state.json"
                node_version  = 1
            }
            
            $node | ConvertTo-Json -Compress | Add-Content $L1NodesFile -Encoding UTF8
        }
        catch {}
    }
    
    # Trust Map
    $trustFile = Join-Path "D:\Infinite\Infinity\Runtime\Listener" "Lattice_Trust_Map.json"
    if (Test-Path $trustFile) {
        try {
            $map = Get-Content $trustFile -Raw | ConvertFrom-Json
            if ($map.items) {
                foreach ($key in $map.items.PSObject.Properties.Name) {
                    $item = $map.items.$key
                    
                    $subj = $key
                    $score = $item.trust
                    $lastUpd = $item.last_updated
                    
                    $idStr = "TRUST_$($subj)_$($lastUpd)"
                    $nodeId = Get-NodeID $idStr
                    
                    $evRefs = @()
                    
                    $node = @{
                        id            = $nodeId
                        type          = "L1_NODE"
                        l1_type       = "CONCLUSION"
                        subject       = $subj
                        score         = $score
                        confidence_n  = $item.n
                        ts            = $lastUpd
                        evidence_refs = $evRefs
                        source_file   = "Lattice_Trust_Map.json"
                        node_version  = 1
                    }
                    
                    $node | ConvertTo-Json -Compress | Add-Content $L1NodesFile -Encoding UTF8
                }
            }
        }
        catch {}
    }
    
    return $state
}

function Link-And-Validate {
    Write-Host "[Compiler] Linking & Validating..." -ForegroundColor Cyan
    
    $l0 = @{}
    if (Test-Path $L0NodesFile) {
        Get-Content $L0NodesFile | ConvertFrom-Json | ForEach-Object { 
            $val = $_
            $l0["$($val.id)"] = $val
            if ($val.raw_data_ref) {
                $refKey = "runlog:$($val.raw_data_ref)"
                $l0[$refKey] = $val 
            }
        }
    }
    
    $l1 = @()
    if (Test-Path $L1NodesFile) {
        $l1 = Get-Content $L1NodesFile | ConvertFrom-Json
    }
    
    $edges = @()
    $violations = @()
    
    foreach ($conc in $l1) {
        $supported = $false
        
        if ($conc.evidence_refs) {
            foreach ($ref in $conc.evidence_refs) {
                if ($l0.ContainsKey($ref)) {
                    $targetParams = "$($conc.id)$($ref)"
                    $edgeId = Get-NodeID $targetParams
                    $edge = @{
                        id     = $edgeId
                        from   = $conc.id
                        to     = $l0[$ref].id
                        rel    = "SUPPORTED_BY"
                        weight = 1.0
                        basis  = "direct_ref"
                    }
                    $edges += $edge
                    $supported = $true
                }
            }
        }
        
        if (-not $supported) {
            $vParams = "$($conc.id)ORPHAN"
            $vId = Get-NodeID $vParams
            
            $violations += @{
                id      = $vId
                l1_id   = $conc.id
                subject = $conc.subject
                issue   = "ORPHAN_NODE"
                desc    = "No valid L0 edge found"
            }
        }
    }
    
    if ($edges.Count -gt 0) {
        $edges | ConvertTo-Json -Compress | Add-Content $EdgesFile -Encoding UTF8
    }
    
    $status = "INTEGRITY_VERIFIED"
    if ($violations.Count -gt 0) { $status = "INTEGRITY_WARNING" }
    
    $report = @{
        ts              = (Get-Date).ToUniversalTime().ToString("o")
        node_count_l0   = $l0.Count 
        node_count_l1   = $l1.Count
        edge_count      = $edges.Count
        violation_count = $violations.Count
        violations      = $violations
        status          = $status
    }
    
    $report | ConvertTo-Json -Depth 5 | Set-Content $ReportFile -Encoding UTF8
    
    Write-Host "Compile Complete. Status: $status"
}

if ($Action -eq "COMPILE") {
    $state = Get-State
    $state = Ingest-L0 $state
    $state = Ingest-L1 $state
    $state.last_compile_ts = (Get-Date).ToUniversalTime().ToString("o")
    Save-State $state
    
    Link-And-Validate
}
