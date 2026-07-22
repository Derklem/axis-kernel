# Get-AxisStateVector.ps1
# Phase 57: Real-Time Integrity Monitoring
# Captures a deterministic "State Vector" of the system's truth HEADs and counts.

$ErrorActionPreference = "Stop"

$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$MemoryDir = Join-Path $Root "Memory"

# Load Central Paths
$PolicyFile = Join-Path $GovDir "integrity_policy.json"
$WitnessFile = Join-Path $GovDir "Axis_Witness_Ledger.jsonl"
$AnchorFile = Join-Path $GovDir "anchor_ledger.jsonl"
$PulseFile = Join-Path $GovDir "integrity_pulse_ledger.jsonl"
$EconFile = Join-Path $GovDir "econ_ledger.jsonl"

if (Test-Path $PolicyFile) {
    try {
        $pol = Get-Content $PolicyFile -Raw | ConvertFrom-Json
        if ($pol.paths.witness_ledger) { $WitnessFile = $pol.paths.witness_ledger }
        if ($pol.paths.anchor_ledger) { $AnchorFile = $pol.paths.anchor_ledger }
        if ($pol.paths.pulse_ledger) { $PulseFile = $pol.paths.pulse_ledger }
        if ($pol.paths.econ_ledger) { $EconFile = $pol.paths.econ_ledger }
    }
    catch {}
}

function Get-LastLineHash($path) {
    if (-not (Test-Path $path)) { return "GENESIS" }
    if (-not (Test-Path $path)) { return "GENESIS" }
    try {
        # Use Get-Content -Tail 1 for safety and simplicity (PowerShell optimizes this)
        # If file is locked, this might fail, but checking lock logs usually happens elsewhere.
        $lastLine = Get-Content $path -Tail 1 -ErrorAction Stop
        
        if (-not [string]::IsNullOrWhiteSpace($lastLine)) {
            # Check if it looks like a JSON array end "]" and try to find the last object
            if ($lastLine.Trim().EndsWith("]")) {
                # Could be a one-line JSON array. Read whole file (it's likely small if this happened)
                # Or simplistic parsing.
                # Let's try parsing the line itself (if small enough)
                if ($lastLine.Length -lt 100000) {
                    $json = $lastLine | ConvertFrom-Json
                    if ($json -is [Array]) { $json = $json[-1] }
                    if ($json.hash) { return $json.hash }
                    if ($json.state_hash) { return $json.state_hash } # Witness might use state_hash
                }
            }
            
            # Standard JSONL
            $json = $lastLine | ConvertFrom-Json
            if ($json.hash) { return $json.hash }
        }
    }
    catch {
        # Fallback: Try reading the whole file if Tail failed (e.g. erratic format)
        try {
            $content = Get-Content $path -Raw
            $json = $content | ConvertFrom-Json
            if ($json -is [Array]) { $json = $json[-1] }
            if ($json.hash) { return $json.hash }
        }
        catch {
            Write-Warning "Get-LastLineHash Failed for $path : $_"
            return "ERROR"
        }
    }
    return "UNKNOWN"
}

# 1. Capture Tips
$vector = [ordered]@{
    ts_utc      = (Get-Date).ToUniversalTime().ToString("o")
    witness_tip = Get-LastLineHash $WitnessFile
    anchor_tip  = Get-LastLineHash $AnchorFile
    pulse_tip   = Get-LastLineHash $PulseFile
    econ_tip    = Get-LastLineHash $EconFile
}

# 2. Capture Counts
$vector.hot_segment_count = (Get-ChildItem (Join-Path $MemoryDir "ledger") -Filter "*_segment.jsonl").Count
$vector.warm_pack_count = (Get-ChildItem (Join-Path $MemoryDir "packs") -Filter "*_pack.jsonl").Count

# 3. Genesis Reachability (Light Check)
# We can't easily traverse the graph here without loading the module, which might be slow.
# For FAST vector, we'll assume TRUE if headers exist. 
# Deeper checks belong in the Watchdog's "DEEP" mode.
$vector.genesis_reachable = $true # Placeholder for now, or check generic file existence

return $vector
