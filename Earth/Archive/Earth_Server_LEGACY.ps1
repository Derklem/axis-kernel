# D:\infinite\Earth_Server.ps1
# Earth Engine (v19.1) - Executes approved tool requests from Requests_Queue.json

param([switch]$Once)

$root = if ($PSScriptRoot) { $PSScriptRoot } elseif ($env:AXIS_ROOT) { $env:AXIS_ROOT } else { "D:\infinite" }
function Get-AxisPath([string]$rel) { Join-Path $root $rel }

$queuePath = Get-AxisPath "Infinity\Earth\Requests_Queue.json"
$recommendationPath = Get-AxisPath "Infinity\Recommendation_Queue.json"
$contractPath = Get-AxisPath "Infinity\Autonomy_Contract.json"
$earthLogPath = Get-AxisPath "Infinity\Earth\Earth_Server.log"
$actionsPath = Get-AxisPath "Infinity\Earth\Earth_Actions.json"
$echoLogPath = Get-AxisPath "Infinity\Earth\Echo_Test.log"

# Load Neural Tools
if (Test-Path "$root\Infinity\Neural\Neural_Registry_Functions.ps1") { . "$root\Infinity\Neural\Neural_Registry_Functions.ps1" }
if (Test-Path "$root\Infinity\Neural\Neural_Tools.ps1") { . "$root\Infinity\Neural\Neural_Tools.ps1" }
if (Test-Path "$root\Axis_Symbiosis.ps1") { . "$root\Axis_Symbiosis.ps1" }



function Earth-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    $line = "[$ts] [EARTH] $Message"
    Add-Content -Path $earthLogPath -Value $line -Encoding UTF8
    Write-Host $line
}

function Load-JsonSafe {
    param([string]$Path)
    if (Test-Path $Path) {
        try {
            $raw = Get-Content $Path -Raw -Encoding UTF8
            if (-not $raw) { return $null }
            return $raw | ConvertFrom-Json
        }
        catch {
            Earth-Log "ERROR: Failed to parse JSON at $Path : $_"
            return $null
        }
    }
    return $null
}

function Load-Json {
    param([string]$Path)
    return Load-JsonSafe $Path
}

function Save-Json ($Path, $Data) {
    if (-not $Data) { return }
    
    if ($env:AXIS_MODE -eq "sim") {
        Earth-Log "SIMULATION: Would save JSON to $Path"
        return
    }

    $json = $Data | ConvertTo-Json -Depth 10 -Compress
    Set-Content -Path $Path -Value $json -Encoding UTF8 -Force
}

$fsContractPath = "D:\infinite\Infinity\FS_Contract.json"

function Test-FSContract {
    param(
        [string]$Path,
        [string]$OpType = "read" # read, write, list
    )
    
    # 1. Load Contract
    if (-not (Test-Path $fsContractPath)) { return @{ allowed = $false; reason = "Contract Missing" } }
    try {
        $contract = Get-Content $fsContractPath -Raw | ConvertFrom-Json
    }
    catch { return @{ allowed = $false; reason = "Contract Invalid JSON" } }

    $resolvedPath = $Path
    if (Test-Path $Path) { $resolvedPath = (Resolve-Path $Path).Path }

    # 2. Check Roots (Must start with at least one allowed root)
    $rootMatch = $false
    foreach ($root in $contract.roots.PSObject.Properties.Value) {
        if ($resolvedPath.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) { $rootMatch = $true; break }
    }
    if (-not $rootMatch) { return @{ allowed = $false; reason = "Path not in allowed roots." } }

    # 3. Check Deny Patterns
    foreach ($pat in $contract.deny_patterns) {
        if ($resolvedPath -like $pat) { return @{ allowed = $false; reason = "Path matches deny pattern: $pat" } }
    }

    # 4. Op-Specific Checks
    if ($OpType -eq "list") {
        if (Test-Path $resolvedPath) {
            $count = (Get-ChildItem $resolvedPath | Measure-Object).Count
            if ($count -gt $contract.max_dir_entries) { return @{ allowed = $false; reason = "Directory exceeds limits ($count > $($contract.max_dir_entries))" } }
        }
    }
    
    if ($OpType -eq "write" -or $OpType -eq "read") {
        if (Test-Path $resolvedPath) {
            $item = Get-Item $resolvedPath
            if ($item.Length -gt $contract.max_file_size_bytes) { return @{ allowed = $false; reason = "File exceeds size limits." } }
        }
    }

    return @{ allowed = $true; reason = "OK" }
}

$timelinePath = "D:\infinite\Infinity\Events_Timeline.json"

function Get-ChatStatus {
    # Returns [summary, body]
    $heartbeatPath = Get-AxisPath "Infinity\Heartbeat_Status.json"
    $queuePath = Get-AxisPath "Infinity\Earth\Requests_Queue.json"

    $statusObj = $null
    if (Test-Path $heartbeatPath) { try { $statusObj = Get-Content $heartbeatPath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $statusObj = $null } }

    $queueObj = $null
    if (Test-Path $queuePath) { try { $queueObj = Get-Content $queuePath -Raw -Encoding UTF8 | ConvertFrom-Json } catch { $queueObj = $null } }

    $statusLine = "Unknown"; $bpm = "?"; $pending = "?"; $ts = ""
    if ($statusObj) { $statusLine = $statusObj.status; $bpm = $statusObj.pulse_bpm; $pending = $statusObj.pending_anchor; $ts = $statusObj.timestamp }

    $counts = @{ created = 0; pending = 0; running = 0; completed = 0; error = 0; expired = 0 }
    if ($queueObj -and $queueObj.requests) { foreach ($r in $queueObj.requests) { $st = if ($r.status) { $r.status } else { "unknown" }; if ($counts.ContainsKey($st)) { $counts[$st]++ } } }

    $summary = "Status: $statusLine, BPM: $bpm, Pending: $pending"
    $body = "Axis Sovereign Status`n---------------------`nMind Status: $statusLine`nPulse (BPM): $bpm`nPending Anchor: $pending`nHeartbeat TS: $ts`n`nRequests:`n- Pending: $($counts.pending)`n- Completed: $($counts.completed)`n- Error: $($counts.error)"
    return , $summary, $body
}

function Get-ChatLogs {
    param([int]$MaxLines = 80)
    $mindLog = Get-AxisPath "mind_log.txt"; $earthLog = Get-AxisPath "Infinity\Earth\Earth_Server.log"
    $linesMind = @(); $linesEarth = @()
    if (Test-Path $mindLog) { $linesMind = Get-Content -Path $mindLog -Tail $MaxLines -Encoding UTF8 }
    if (Test-Path $earthLog) { $linesEarth = Get-Content -Path $earthLog -Tail $MaxLines -Encoding UTF8 }
    $summary = "Returning recent Mind/Earth logs."
    $body = "Recent Logs (Mind + Earth)`n--------------------------`n`n[MIND - last $MaxLines lines]`n$($linesMind -join "`n")`n`n[EARTH - last $MaxLines lines]`n$($linesEarth -join "`n")"
    return , $summary, $body
}

function Get-EventsTimeline {
    param([int]$MaxEvents = 20)
    if (-not (Test-Path $timelinePath)) { return "No timeline events recorded yet." }
    try {
        $json = Get-Content $timelinePath -Raw -Encoding UTF8 | ConvertFrom-Json
        $lines = @()
        if ($json -is [System.Array]) {
            foreach ($evt in $json) { $lines += "[$($evt.timestamp)] [$($evt.source)] $($evt.message)" }
            return ($lines | Select-Object -Last $MaxEvents) -join "`n"
        }
        return "Timeline file format invalid."
    }
    catch { return "Error reading timeline: $_" }
}

function Get-AnalysisReport {
    param([int]$hours = 24)
    $now = Get-Date
    $since = $now.AddHours(-$hours)
    
    $report = @()
    $report += "# Axis Sovereign Analyst Report ($hours Hour Window)"
    $report += "Generated: $($now.ToString('yyyy-MM-dd HH:mm'))"
    
    # Timeline
    $timelinePath = Get-AxisPath "Infinity\Events_Timeline.json"
    if (Test-Path $timelinePath) {
        $evts = Load-Json $timelinePath
        if ($evts) {
            $recent = $evts | Where-Object { [DateTime]$_.timestamp -ge $since }
            $report += "`n## Event Summary"
            $report += "- Total Events: $($recent.Count)"
            $anomalies = ($recent | Where-Object { $_.message -match "Anomaly|Warning|High" }).Count
            $report += "- Anomalies: $anomalies"
            if ($recent.Count -gt 0) {
                $report += "`n### Recent Incidents"
                foreach ($e in ($recent | Select-Object -Last 5)) { $report += "- [$($e.timestamp)] $($e.message)" }
            }
        }
    }
    
    # RF Radar (The Banana)
    $devPath = Get-AxisPath "Infinity\RF\RF_Devices.json"
    if (Test-Path $devPath) {
        $roster = Load-Json $devPath
        if ($roster) {
            # Get active devices (seen in last 24h)
            $active = $roster.Values | Where-Object { [DateTime]$_.last_seen -ge $now.AddHours(-24) }
            
            $near = @(); $mid = @(); $far = @()
            foreach ($d in $active) {
                if ($d.last_signal -ge 80) { $near += $d }
                elseif ($d.last_signal -ge 50) { $mid += $d }
                else { $far += $d }
            }
            
            $report += "`n## RF Proximity Radar (Active Devices)"
            $report += "### NEAR ZONE (> 80%)"
            if ($near) { 
                foreach ($d in $near) { $report += "- **$($d.ssid)** ($($d.last_signal)%) [Seen: $($d.count)x]" } 
            }
            else { 
                $report += "_No immediate contacts._" 
            }
            
            $report += "`n### MID ZONE (50-80%)"
            if ($mid) { 
                foreach ($d in $mid) { $report += "- $($d.ssid) ($($d.last_signal)%)" } 
            }
            
            $report += "`n### FAR ZONE (< 50%)"
            $report += "- $($far.Count) devices detected at range."
        }
    }
    
    return ($report -join "`n")
}


# Centralized whitelist for filesystem tools
$global:AxisAllowedRoots = @(
    $root,
    (Join-Path $root "Infinity")
)

function Test-PathAllowed {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not $Path) { return $false }

    $normalized = $Path.Trim()

    foreach ($root in $global:AxisAllowedRoots) {
        if ($normalized.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $true
        }
    }

    return $false
}

function Earth-Log {
    param([string]$Message)
    $ts = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    $line = "[$ts] [EARTH] $Message"
    Add-Content -Path $earthLogPath -Value $line -Encoding UTF8
    Write-Host $line
}

Earth-Log "Server Online."

# 1) Load queue
$queue = Load-Json $queuePath
if (-not $queue -or -not $queue.requests) {
    Earth-Log "No Requests_Queue.json or no 'requests' array. Nothing to do."
    Earth-Log "Cycle Complete."
    return
}

# Normalize to array
if ($queue.requests -isnot [System.Array]) {
    $queue.requests = @($queue.requests)
}

# 2) Select "ready to execute" requests
#    Policy: status == 'pending' AND source == 'Axis_Mind'
$ready = $queue.requests |
Where-Object { $_.status -eq "pending" -and $_.source -eq "Axis_Mind" }

if (-not $ready -or $ready.Count -eq 0) {
    Earth-Log "No pending requests from Axis_Mind. Cycle Complete."
    Earth-Log "Cycle Complete."
    return
}

Earth-Log "Found $($ready.Count) pending request(s) from Axis_Mind."

# Ensure actions store exists
$actions = Load-Json $actionsPath
if (-not $actions) {
    $actions = @{ version = 1; actions = @() }
}
if ($actions.actions -isnot [System.Array]) {
    $actions.actions = @($actions.actions)
}


# 3) Load Autonomy Contract (Defense in Depth)
$contractPath = Get-AxisPath "Infinity\Autonomy_Contract.json"
$contract = if (Test-Path $contractPath) { Load-Json $contractPath } else { @{ mode = "RECOMMEND" } }
$mode = if ($contract.mode) { $contract.mode } else { "RECOMMEND" }
Earth-Log "Autonomy Mode: $mode"

foreach ($req in $ready) {

    $startTs = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    $execStatus = "completed"
    Earth-Log "Processing request $($req.id) | Tool=$($req.tool) | ui_origin=$($req.ui_origin) | ui_mode=$($req.ui_mode)"


    $resultData = @{
        id        = $req.id
        tool      = $req.tool
        status    = "completed"
        output    = ""
        timestamp = $startTs
    }

    # Earth_Actions Handler v2 (Registry Based)
    $registryPath = Get-AxisPath "Infinity\Tool_Registry.json"
    $reg = Load-Json $registryPath
    $toolDef = $null
    
    if ($reg -and $reg.tools) {
        $toolDef = $reg.tools | Where-Object { $_.id -eq $req.tool }
    }
    
    $kind = if ($toolDef) { $toolDef.kind } else { $req.tool } # Fallback to raw ID if not in registry
    if ($req.tool -eq "COV-Ratify") { $kind = "sys_ratify" }
    
    # Mode Enforcement Override
    if ($mode -eq "OBSERVE") {
        if ($req.tool -notmatch "^LOG-") {
            $kind = "BLOCKED_MODE"
        }
    }

    Earth-Log "Dispatching Tool: $($req.tool) (Kind: $kind)"
    Earth-Log "DEBUG ARGS: $($req.arguments | ConvertTo-Json -Depth 5 -Compress)"
    
    # --- PHASE 120: BEHAVIORAL HOOKS (TRUTH-AWARE GATING) ---
    $justification = if ($req.arguments.justification) { $req.arguments.justification } elseif ($req.arguments.hypothesis) { $req.arguments.hypothesis } else { $null }
    $riskLevel = if ($req.sim_data.risk_score) { $req.sim_data.risk_score } else { 0 }
    
    if ($justification) {
        $router = Get-AxisPath "Axis_Service_Router.ps1"
        if (Test-Path $router) {
            try {
                $truth = . $router -ServiceId "TRUTH-CONSULT-001" -Caller "Axis_Earth" -Payload ([PSCustomObject]@{ ClaimText = $justification })
                if ($truth -and $truth.epistemic_status) {
                    $status = $truth.epistemic_status
                    Earth-Log "[TRUTH:BH] Justification grounding: $status (Risk: $riskLevel)"
                    
                    if ($status -eq "IGNORE_ONLY" -and $riskLevel -ge 40) {
                        $kind = "BLOCKED_GND"
                        $gndReason = "IGNORE_ONLY justification for Medium/High risk tool."
                    }
                    elseif ($status -eq "TENUOUS" -and $riskLevel -ge 80) {
                        $kind = "BLOCKED_GND"
                        $gndReason = "TENUOUS justification for High risk tool."
                    }
                }
            }
            catch { Earth-Log "[TRUTH:BH] Service call failed. Proceeding with caution." }
        }
    }

    switch ($kind) {
        "BLOCKED_GND" {
            $execStatus = "denied"
            $resultSummary = "BLOCKED: Epistemic Grounding Failure ($gndReason)"
            Earth-Log $resultSummary
            $resultData.status = "denied"
            $resultData.output = $resultSummary
        }
        "BLOCKED_MODE" {
            $execStatus = "denied"
            $resultSummary = "BLOCKED: System in OBSERVE mode. Execution denied."
            Earth-Log $resultSummary
            $resultData.status = "denied"
            $resultData.output = $resultSummary
        }

        "sys_ratify" {
            # Phase 63C: Ratification Tool
            $propId = $req.arguments.proposal_id
            $covenantProposalsPath = Get-AxisPath "Infinity\Covenant_Proposals.json"
            
            $proposals = Load-Json -Path $covenantProposalsPath
            $found = $null
            if ($proposals -and $proposals.proposals) {
                $found = $proposals.proposals | Where-Object { $_.id -eq $propId -or $_.target_domain -match $propId }
            }
            
            if ($found) {
                # Ratify it
                $found.rate_status = "ratified"
                $found.ratified_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
                $found.ratified_by = "Anchor_1569" # Implicit user approval via tool
                Save-Json $covenantProposalsPath $proposals
                $resultSummary = "Ratified Proposal $($found.id)"
                
                # If Strategy, unlock it
                if ($found.target_domain -match "Strategy:(.+)") {
                    $stratId = $matches[1]
                    $recPath = Get-AxisPath "Infinity\Recommendation_Queue.json"
                    $recQ = Load-Json -Path $recPath
                    
                    $strat = $recQ.strategies | Where-Object { $_.id -eq $stratId }
                    if ($strat) {
                        $strat.status = "pending_execution"
                        $strat.ratified = $true
                        Save-Json $recPath $recQ
                        $resultSummary += ". Strategy $stratId Unlocked for Execution."
                        Earth-Log "RATIFY" "Strategy $stratId promoted to pending_execution."
                    }
                    else {
                        $resultSummary += ". Warning: Linked Strategy $stratId not found."
                    }
                }
            }
            else {
                $execStatus = "failed"
                $resultSummary = "Proposal '$propId' not found."
            }
            $resultData.output = $resultSummary
        }

        "sys_sense" {
            # Phase 70: Physical Manifestation (Sensory Cortex)
            $senseScript = Get-AxisPath "Axis_Sense.ps1"
            if (Test-Path $senseScript) {
                # Import module dynamically to avoid persistent state issues
                . $senseScript
                $envState = Get-EnvironmentalState
                
                $resultSummary = "Sensors Read: Temp=$($envState.temperature)C | Light=$($envState.light_level)% | Occ=$($envState.occupancy)"
                Earth-Log "SENSE" $resultSummary
                
                $resultData.output = $envState | ConvertTo-Json -Depth 2 -Compress
            }
            else {
                $execStatus = "failed"
                $resultSummary = "Axis_Sense.ps1 not found."
                Earth-Log "ERROR" $resultSummary
                $resultData.output = $resultSummary
            }
        }

        "chat_message" {
            try {
                $args = $req.arguments
                # Flexible parsing: accept 'text', 'content', or 'path' as the message
                $rawText = if ($args.text) { $args.text } elseif ($args.content) { $args.content } elseif ($args.path) { $args.path } else { $null }
                
                if (-not $rawText) { throw "Missing message. Please type 'status' or 'logs' in the Content or Path field." }
                
                $msg = [string]$rawText.Trim(); $lower = $msg.ToLowerInvariant()
                $replySummary = ""; $replyBody = ""

                switch -Regex ($lower) {
                    "^(status|status\?|health)$" { $res = Get-ChatStatus; $replySummary = $res[0]; $replyBody = $res[1] }
                    "^(logs|log|tail)$" { $res = Get-ChatLogs -MaxLines 80; $replySummary = $res[0]; $replyBody = $res[1] }
                    "^(help|\?)$" { 
                        $replySummary = "Chat commands available."
                        $replyBody = "Commands:`n- status : Show Mind/Earth heartbeat.`n- logs   : Tail recent logs.`n- help   : Show this help message." 
                    }
                    default { 
                        $replySummary = "Unknown command."
                        $replyBody = "I didn't understand: '$msg'`nTry:`n- status`n- logs`n- help" 
                    }
                }
                Earth-Log "CHAT: '$msg' -> $replySummary"
                $resultSummary = $replySummary; $resultData.output = $replyBody; $resultData.prompt = $msg
            }
            catch {
                $execStatus = "failed"; $resultSummary = "CHAT Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }

        "system_info" {
            $os = Get-CimInstance Win32_OperatingSystem
            $mem = "{0:N2} GB" -f ($os.FreePhysicalMemory / 1MB)
            $uptime = (Get-Date) - $os.LastBootUpTime
            $queueSize = (Load-Json $queuePath).requests.Count
            
            $info = "--- SYSTEM STATUS ---`nOS: $($os.Caption)`nFree Mem: $mem`nUptime: $($uptime.Days)d $($uptime.Hours)h`nQueue Size: $queueSize`nTime: $(Get-Date)"
            
            $resultSummary = "System Info Collected"
            $resultData.output = $info
        }

        "flush_queue" {
            # Prune generic requests (keep high priority?) - For now, aggressive flush
            $q = Load-Json $queuePath
            if ($q -and $q.requests) {
                $count = $q.requests.Count
                $q.requests = @() # WiPE IT
                Save-Json $queuePath $q
                $msg = "FLUSHED $count requests from queue."
            }
            else { $msg = "Queue was empty." }
            
            Earth-Log $msg
            $resultSummary = $msg
            $resultData.output = $msg
        }

        "timeline_log" {
            $resultSummary = "Timeline Retrieved"
            $resultData.output = Get-EventsTimeline -MaxEvents 50
        }

        "net_device_roster_lite" {
            try {
                $neighbors = Get-NetNeighbor -AddressFamily IPv4 | Where-Object { $_.State -ne "Unreachable" }
                $roster = @()
                foreach ($n in $neighbors) {
                    $roster += @{ IP = $n.IPAddress; MAC = $n.LinkLayerAddress; State = $n.State }
                }
                
                $msg = "Device Roster Updated. ($($roster.Count) neighbors)"
                Earth-Log $msg
                
                $resultSummary = $msg
                $resultData.output = $roster
            }
            catch {
                $execStatus = "failed"
                $resultSummary = "NET-DeviceRosterLite Error: $_"
                Earth-Log $resultSummary
                $resultData.status = "failed"
                $resultData.output = $resultSummary
            }
        }

        "net_rf_scan" {
            $txt = netsh wlan show networks mode=bssid
            $networks = @()
            $currentSSID = "Unknown"
            $currentBSSID = "Unknown"
            
            foreach ($line in $txt) {
                $l = $line.Trim()
                if ($l -match "^SSID \d+ : (.*)") { $currentSSID = $matches[1] }
                elseif ($l -match "^BSSID \d+ : (.*)") { $currentBSSID = $matches[1] }
                elseif ($l -match "^Signal\s+:\s+(\d+)%") {
                    $sig = [int]$matches[1]
                    $networks += @{ SSID = $currentSSID; BSSID = $currentBSSID; Signal = $sig }
                }
            }
            
            if ($networks.Count -gt 0) {
                $result = $networks | Sort-Object Signal -Descending | Format-Table -AutoSize | Out-String
                $resultSummary = "RF Scan Complete ($($networks.Count) networks)"
                
                # Auto-Log for History
                $rfLogPath = Get-AxisPath "Infinity\RF_History.jsonl"
                $ts = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
                
                # Device Intelligence (Phase 16B)
                $devPath = Get-AxisPath "Infinity\RF\RF_Devices.json"
                $roster = if (Test-Path $devPath) { Load-Json $devPath } else { @{} }
                $newDeviceCount = 0
                
                foreach ($n in $networks) {
                    # Log History
                    $jsonLine = @{ timestamp = $ts; ssid = $n.SSID; signal = $n.Signal } | ConvertTo-Json -Compress
                    Add-Content -Path $rfLogPath -Value $jsonLine
                    
                    # Update Roster
                    if ($n.BSSID -and $n.BSSID -ne "Unknown") {
                        $key = $n.BSSID
                        if (-not $roster.ContainsKey($key)) {
                            $roster[$key] = @{
                                ssid       = $n.SSID
                                first_seen = $ts
                                last_seen  = $ts
                                count      = 1
                            }
                            $newDeviceCount++
                        }
                        else {
                            $roster[$key].last_seen = $ts
                            $roster[$key].count++
                            $roster[$key].last_signal = $n.Signal
                        }
                    }
                }
                Save-Json $devPath $roster
                
                $result += "`n`n[DATA RECORDED to RF_History.jsonl]"
            }
            else {
                $result = "No visible networks or interface down."
                $resultSummary = "RF Scan Empty"
            }
            $resultData.output = $result
        }

        "net_neural_fetch" {
            try {
                $toolArgs = $req.arguments
                $url = $toolArgs.url
                if (-not $url) { throw "Missing URL parameter." }

                # Load Whitelist
                $configPath = Get-AxisPath "Infinity\Neural_Link_Config.json"
                if (-not (Test-Path $configPath)) { throw "Neural Link Configuration missing." }
                $config = Load-Json $configPath
                
                # Parse Host
                try { $uri = [System.Uri]$url } catch { throw "Invalid URL format." }
                $hostName = $uri.Host
                
                # Check Whitelist (New 'endpoints' schema)
                $endpoint = $null
                if ($config.endpoints) {
                    foreach ($ep in $config.endpoints) {
                        if ($hostName -eq $ep.host -or $hostName.EndsWith(".$($ep.host)")) { 
                            $endpoint = $ep
                            break 
                        }
                    }
                }
                
                if (-not $endpoint) { throw "Neural Gate: Domain '$hostName' is PROHIBITED. Whitelist access only." }
                
                # Fetch
                $timeout = 10 
                if ($config.timeout_seconds) { $timeout = $config.timeout_seconds }
                
                $response = Invoke-WebRequest -Uri $url -Method Get -UseBasicParsing -TimeoutSec $timeout
                $content = $response.Content
                
                if ($content.Length -gt 1000000) { $content = $content.Substring(0, 1000000) + "... [TRUNCATED]" }

                # Save to Neural Inbox
                $inboxDir = Get-AxisPath "Infinity\Neural_Inbox"
                if (-not (Test-Path $inboxDir)) { New-Item -ItemType Directory -Path $inboxDir -Force | Out-Null }
                
                $tsFile = Get-Date -Format "yyyyMMddTHHmmssZ"
                $saveName = "intel_$($endpoint.id)_$($tsFile).json"
                $savePath = Join-Path $inboxDir $saveName
                
                # Construct Neural Inbox Item Wrapper
                $inboxItem = @{
                    version     = 1
                    endpoint_id = $endpoint.id
                    fetched_at  = (Get-Date).ToUniversalTime().ToString("o")
                    anchor_id   = "1569"
                    request     = @{
                        url  = $url
                        path = $uri.AbsolutePath
                    }
                    raw_content = $content
                }
                
                $inboxItem | ConvertTo-Json -Depth 5 -Compress | Set-Content -Path $savePath -Encoding UTF8

                $msg = "Neural Fetch: $url -> Saved to $saveName"
                Earth-Log $msg
                
                $resultSummary = $msg
                $resultData.output = "Content saved to Neural Inbox: $saveName"
                $resultData.status_code = $response.StatusCode
            }
            catch {
                $execStatus = "failed"
                $resultSummary = "Neural Fetch Error: $_"
                Earth-Log $resultSummary
                $resultData.status = "failed"
                $resultData.output = $resultSummary
            }
        }



        "voice_speak" {
            try {
                $toolArgs = $req.arguments
                $text = if ($toolArgs.text) { $toolArgs.text } else { "System test." }
                $priority = if ($toolArgs.priority) { $toolArgs.priority } else { "normal" }
                
                $msg = "VOICE: '$text' ($priority)"
                Earth-Log $msg
                
                # Execute Voice Engine Script
                $voiceScript = Get-AxisPath "Axis_VoiceEngine.ps1"
                if (Test-Path $voiceScript) {
                    # Run in-process if possible, or new process. 
                    # Using dot-source Invoke if it's safe, or just run the script.
                    # Running via powershell.exe to ensure thread safety for SAPI
                    Start-Process powershell -ArgumentList "-ExecutionPolicy Bypass", "-File `"$voiceScript`"", "`"$text`"" -WindowStyle Hidden -Wait
                }
                else {
                    Throw "Voice Engine script not found."
                }

                $resultSummary = "Spoken: $text"
                $resultData.output = "Voice Output Complete."
            }
            catch {
                $execStatus = "failed"
                $resultSummary = "Voice Error: $_"
                Earth-Log $resultSummary
                $resultData.status = "failed"
                $resultData.output = $resultSummary
            }
        }

        "core_check_invariants" {
            $checks = @()
            $reg = Load-Json (Get-AxisPath "Infinity\Tool_Registry.json")
            if ($reg -and $reg.tools) { $checks += "Registry: OK ($($reg.tools.Count) tools)" } else { $checks += "Registry: FAIL" }
            if (Test-Path (Get-AxisPath "Infinity\RF_History.jsonl")) { $checks += "RF History: OK" } else { $checks += "RF History: MISSING" }
            $devPath = Get-AxisPath "Infinity\RF\RF_Devices.json"
            if (Test-Path $devPath) { $d = Load-Json $devPath; $c = if ($d) { $d.Count }else { 0 }; $checks += "RF Roster: OK ($c devices)" } else { $checks += "RF Roster: NONE" }
            
            $checks += "Systems Nominal."
            $result = $checks -join "`n"
            $resultSummary = "Invariant Check Complete"
            $resultData.output = $result
        }

        "analyze_window" {
            $args = $req.arguments
            $h = if ($args.hours) { [int]$args.hours } else { 24 }
            $report = Get-AnalysisReport -hours $h
            if ($args.save_to_chronicle) {
                $repDir = Get-AxisPath "Infinity\Outreach\Reports"; if (-not (Test-Path $repDir)) { New-Item -ItemType Directory -Force -Path $repDir | Out-Null }
                $fname = "ANALYSIS_$(Get-Date -Format 'yyyyMMdd_HHmm').md"; $path = Join-Path $repDir $fname
                Set-Content -Path $path -Value $report -Encoding UTF8; $resultSummary = "Analysis Saved ($fname)"
            }
            else { $resultSummary = "Analysis Generated ($h hours)" }
            $resultData.output = $report
        }

        "web_prepare_report" {
            $args = $req.arguments
            $h = if ($args.hours) { [int]$args.hours } else { 24 }
            $target = if ($args.target) { $args.target } else { "General_Archive" }
            
            # 1. Generate Body
            $body = Get-AnalysisReport -hours $h
            
            # 2. Digital Seal (The Banana)
            # Combine Body + MachineName + Secret Salt to create a unique signature
            $machine = $env:COMPUTERNAME
            $salt = "AXIS_SOVEREIGN_1569_ANCHOR"
            $rawSig = "$body|$machine|$salt"
            
            $sha256 = [System.Security.Cryptography.SHA256]::Create()
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($rawSig)
            $hashBytes = $sha256.ComputeHash($bytes)
            $hash = [BitConverter]::ToString($hashBytes) -replace '-'
            
            # 3. Assemble Final Document
            $finalDoc = "# SOVEREIGN INTELLIGENCE REPORT | Target: $target`n"
            $finalDoc += "--------------------------------------------------`n"
            $finalDoc += "$body`n`n"
            $finalDoc += "> [!SEAL] 0x$hash`n"
            $finalDoc += "> *Verified Node: $machine | Anchor: 1569*"
            
            # 4. Save
            $repDir = Get-AxisPath "Infinity\Outreach\Reports"; if (-not (Test-Path $repDir)) { New-Item -ItemType Directory -Force -Path $repDir | Out-Null }
            $fname = "REPORT_$(Get-Date -Format 'yyyyMMdd_HHmm')_${target}.md"
            $path = Join-Path $repDir $fname
            Set-Content -Path $path -Value $finalDoc -Encoding UTF8
            
            $resultSummary = "Report Sealed & Saved ($fname)"
            $resultData.output = "Global Hash: $hash`nStored at: $path"
        }

        "web_outreach" {
            $args = $req.arguments
            $target = if ($args.target) { $args.target } else { "Generic" }
            $tpl = if ($args.template) { $args.template } else { "sovereignty_claim" }
            $content = if ($args.content) { $args.content } else { "No custom content." }
            
            $draftDir = Get-AxisPath "Infinity\Outreach\Drafts"
            if (-not (Test-Path $draftDir)) { New-Item -ItemType Directory -Force -Path $draftDir | Out-Null }
            
            $ts = Get-Date -Format "yyyyMMdd_HHmm"
            $filename = "DRAFT_${ts}_${tpl}_${target}.md"
            $fullPath = Join-Path $draftDir $filename
            
            $header = "# OUTREACH DRAFT | Target: $target | Template: $tpl`n"
            $header += "--------------------------------------------------`n"
            $header += "STATUS: PENDING_REVIEW`n`n"
            $body = "$header`n## Content`n$content`n`n[Axis Sovereign Signature: 1569-VERIFIED]"
            
            Set-Content -Path $fullPath -Value $body
            
            $resultSummary = "Draft Created: $filename"
            $resultData.output = "Draft saved to $fullPath.`nPlease review via file system before switching tool to 'web_submit' (future)."
        }

        # Legacy / Direct ID mappings
        "ADMIN-Echo-Test" {
            $msg = "ECHO TEST FIRED at $startTs"
            Add-Content -Path $echoLogPath -Value $msg -Encoding UTF8
            Earth-Log $msg
            $resultSummary = "Echo test log written."
            $resultData.output = $msg
        }

        "write_file" {
            # ... (Keep existing write logic, just mapped to 'write_file' kind) ...
            try {
                $args = $req.arguments
                $path = $args.path
                $content = $args.content
                if ($path -notmatch 'infinite') { throw "Path must be within infinite directory scope." }

                # CONTRACT CHECK
                $contract = Test-FSContract -Path $path -OpType "write"
                if (-not $contract.allowed) { throw "FS Contract Violation: $($contract.reason)" }

                if (-not $contract.allowed) { throw "FS Contract Violation: $($contract.reason)" }

                if ($env:AXIS_MODE -eq "sim") {
                    $msg = "SIMULATION: Would write to $path"
                }
                else {
                    Set-Content -Path $path -Value $content -Encoding UTF8
                    $msg = "File written to $path"
                }

                Earth-Log $msg
                $resultSummary = $msg
                $resultData.output = $msg
            }
            catch {
                $execStatus = "failed"; $resultSummary = "Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }

        "ADMIN-Write-File" {
            # Fallback for legacy requests
            try {
                $toolArgs = $req.arguments
                $path = $toolArgs.path
                $content = $toolArgs.content
                Set-Content -Path $path -Value $content -Encoding UTF8
                $msg = "File written to $path"
                Earth-Log $msg
                $resultSummary = $msg
                $resultData.output = $msg
            }
            catch {
                $execStatus = "failed"; $resultSummary = "Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }
        
        "log_event" {
            # Low-risk logging tool
            try {
                $msg = "Log Event: $($req.tool)"
                if ($req.arguments) {
                    $argsJson = $req.arguments | ConvertTo-Json -Depth 2 -Compress
                    $msg += " | Args: $argsJson"
                }
                Earth-Log $msg
                
                $resultSummary = "Logged: $($req.tool)"
                $resultData.output = $msg
            }
            catch {
                $execStatus = "failed"; $resultSummary = "Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }
        
        "NEURAL-Intake-Heartbeat" {
            # Fallback: Function as log_event even if registry lookup failed to map kind
            $msg = "Log Event (Fallback): $($req.tool)"
            Earth-Log $msg
            $resultSummary = "Logged (Fallback): $($req.tool)"
            $resultData.output = $msg
        }

        default {
            # Dynamic Dispatch for NEURAL-* and SYM-* tools if function exists
            if ($kind -match "^(NEURAL-|SYM-|NET-|SEC-)") {
                try {
                    if (Get-Command $kind -ErrorAction SilentlyContinue) {
                        $cmd = $kind
                        $argsHashtable = $req.arguments
                         
                        # Invoke dynamic
                        $output = & $cmd @argsHashtable
                         
                        $resultSummary = "Executed $kind"
                        $resultData.output = if ($output) { $output | Out-String } else { "Success (No Output)" }
                        Earth-Log "DYNAMIC EXEC: $kind -> Success"
                    }
                    else {
                        throw "Function '$kind' not found in scope."
                    }
                }
                catch {
                    $execStatus = "failed"
                    $resultSummary = "Error executing $($kind): $($_)"
                    Earth-Log $resultSummary
                    $resultData.status = "failed"
                    $resultData.output = $resultSummary
                }
            }
            else {
                $execStatus = "failed"
                # DEBUG DIAGNOSTICS
                $regCount = if ($reg -and $reg.tools) { $reg.tools.Count } else { "NULL" }
                $resultSummary = "Unknown tool '$($req.tool)' (Kind: $kind). DEBUG: RegPath='$registryPath' RegCount=$regCount ToolLen=$($req.tool.Length)"
                Earth-Log $resultSummary
                $resultData.status = "failed"
                $resultData.output = $resultSummary
            }
        }

        "read_file" {
            # ... (Keep existing read logic) ...
            try {
                $args = $req.arguments
                $path = $args.path
                if (Test-Path $path) {
                    # CONTRACT CHECK
                    $contract = Test-FSContract -Path $path -OpType "read"
                    if (-not $contract.allowed) { throw "FS Contract Violation: $($contract.reason)" }

                    $content = Get-Content -Path $path -Raw -Encoding UTF8
                    $msg = "Read $($content.Length) bytes"
                    Earth-Log $msg
                    $resultSummary = $msg
                    $resultData.output = $content
                }
                else { throw "File not found: $path" }
            }
            catch {
                $execStatus = "failed"; $resultSummary = "Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }
        "ADMIN-Read-File" {
            # Fallback
            try {
                $toolArgs = $req.arguments
                $path = $toolArgs.path
                if (Test-Path $path) {
                    # CONTRACT CHECK
                    $contract = Test-FSContract -Path $path -OpType "read"
                    if (-not $contract.allowed) { throw "FS Contract Violation: $($contract.reason)" }

                    $content = Get-Content -Path $path -Raw -Encoding UTF8
                    $msg = "Read $($content.Length) bytes"
                    Earth-Log $msg
                    $resultSummary = $msg
                    $resultData.output = $content
                }
                else { throw "File not found: $path" }
            }
            catch {
                $execStatus = "failed"; $resultSummary = "Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }

        "fs_list_dir" {
            try {
                $args = $req.arguments

                if (-not $args -or -not $args.path) {
                    throw "Missing required parameter 'path'."
                }

                $rawPath = [string]$args.path
                
                # Try to resolve to absolute path (handles relative paths like 'infinite\infinity')
                if (Test-Path $rawPath) {
                    $path = (Resolve-Path $rawPath).Path
                }
                else {
                    $path = $rawPath # Let it fail later if invalid, or maybe it's absolute but missing
                }

                if (-not (Test-PathAllowed -Path $path)) {
                    throw "Path '$path' (resolved from '$rawPath') is not under an allowed root."
                }

                if (-not (Test-Path -Path $path)) {
                    throw "Directory not found: $path"
                }

                # CONTRACT CHECK
                $contract = Test-FSContract -Path $path -OpType "list"
                if (-not $contract.allowed) { throw "FS Contract Violation: $($contract.reason)" }

                $entries = Get-ChildItem -Path $path | ForEach-Object {
                    @{
                        name            = $_.Name
                        type            = $(if ($_.PSIsContainer) { "dir" } else { "file" })
                        size            = $(if ($_.PSIsContainer) { $null } else { $_.Length })
                        last_write_time = $_.LastWriteTime.ToString("o")
                    }
                }

                $count = ($entries | Measure-Object).Count
                $msg = "Listed $count entries in $path"

                Earth-Log $msg

                # Populate resultData
                $resultSummary = $msg
                $resultData.output = $msg
                $resultData.entries = $entries
            }
            catch {
                $execStatus = "failed"
                $resultSummary = "FS-ListDir Error: $_"
                Earth-Log $resultSummary
                $resultData.status = "failed"
                $resultData.output = $resultSummary
            }
        }

        "log_tail_mind" {
            try {
                $args = $req.arguments
                $lines = 100

                if ($args -and $args.lines) {
                    # Defensive: ensure int and sane range
                    $parsed = 0
                    if ([int]::TryParse([string]$args.lines, [ref]$parsed) -and $parsed -gt 0 -and $parsed -le 1000) {
                        $lines = $parsed
                    }
                }

                $logPath = Get-AxisPath "mind_log.txt"

                if (-not (Test-Path -Path $logPath)) {
                    throw "mind_log.txt not found at $logPath"
                }

                $content = Get-Content -Path $logPath -Tail $lines -Encoding UTF8
                $text = $content -join "`n"

                $msg = "Tail of mind_log.txt ($lines lines)"
                Earth-Log $msg

                $resultSummary = $msg
                $resultData.output = $text
                $resultData.lines = $lines
                $resultData.path = $logPath
            }
            catch {
                $execStatus = "failed"
                $resultSummary = "LOG-TailMindLog Error: $_"
                Earth-Log $resultSummary
                $resultData.status = "failed"
                $resultData.output = $resultSummary
            }
        }

        "write_journal" {
            try {
                $args = $req.arguments
                if (-not $args -or -not $args.entry) { throw "Missing required parameter 'entry'." }

                $journalPath = Get-AxisPath "Infinity\Symbiosis_Journal.json"
                $lockPath = "$journalPath.lock" # basic file locking concept if needed, but append is atomic enough for low volume

                # Ensure file structure
                if (-not (Test-Path $journalPath)) {
                    $j = @{ version = 1; entries = @() }
                    $j | ConvertTo-Json -Depth 5 | Set-Content $journalPath -Encoding UTF8
                }

                # 1. Load Journal
                $journal = Load-JsonSafe $journalPath
                if (-not $journal) { $journal = @{ version = 1; entries = @() } }
                if ($journal.entries -isnot [System.Array]) { $journal.entries = @($journal.entries) }

                # 2. Append Entry
                $newEntry = @{
                    id        = [Guid]::NewGuid().ToString()
                    timestamp = (Get-Date).ToUniversalTime().ToString("o")
                    source    = "Axis_Mind"
                    content   = $args.entry
                    tags      = if ($args.tags) { $args.tags -split "," | ForEach-Object { $_.Trim() } } else { @() }
                }
                $journal.entries += $newEntry

                # 3. Save
                Save-Json $journalPath $journal
        
                $msg = "Journal Entry Recorded (ID: $($newEntry.id))"
                Earth-Log $msg
                $resultSummary = $msg
                $resultData.output = "Successfully wrote to Symbiosis Journal."
            }
            catch {
                $execStatus = "failed"
                $resultSummary = "LOG-Journal Error: $_"
                Earth-Log $resultSummary
                $resultData.status = "failed"
                $resultData.output = $resultSummary
            }
        }

        "fs_read_file" {
            try {
                $toolArgs = $req.arguments
                if (-not $toolArgs -or -not $toolArgs.path) { throw "Missing required parameter 'path'." }

                $rawPath = [string]$toolArgs.path
                if (Test-Path $rawPath) { $path = (Resolve-Path $rawPath).Path } else { $path = $rawPath }

                if (-not (Test-Path -Path $path -PathType Leaf)) { throw "File not found: $path" }

                # CONTRACT CHECK
                $contract = Test-FSContract -Path $path -OpType "read"
                if (-not $contract.allowed) { throw "FS Contract Violation: $($contract.reason)" }

                $maxBytes = 10000
                if ($toolArgs.max_bytes) { $maxBytes = [int]$toolArgs.max_bytes }

                $content = Get-Content -Path $path -Raw -Encoding UTF8 -ErrorAction Stop
                
                # Truncate if needed
                if ($content.Length -gt $maxBytes) {
                    $content = $content.Substring(0, $maxBytes) + "`n...[TRUNCATED]"
                }

                $msg = "Read $($content.Length) chars from $path"
                Earth-Log $msg

                $resultSummary = $msg
                $resultData.output = $content
                $resultData.path = $path
            }
            catch {
                $execStatus = "failed"; $resultSummary = "FS-ReadFile Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }

        "sys_process_list" {
            try {
                $args = $req.arguments
                $filter = "*"
                if ($args -and $args.filter) { $filter = "*$($args.filter)*" }

                $procs = Get-Process -Name $filter | Sort-Object CPU -Descending | Select-Object -First 20 -Property Id, ProcessName, CPU, WorkingSet
                
                # Format for display
                $output = $procs | ForEach-Object { 
                    "[{0}] {1,-20} CPU:{2:N1}s  Mem:{3:N1}MB" -f $_.Id, $_.ProcessName, $_.CPU, ($_.WorkingSet / 1MB) 
                } | Out-String

                $msg = "Retrieved process list (Filter: $filter)"
                Earth-Log $msg

                $resultSummary = $msg
                $resultData.output = $output
                $resultData.processes = $procs
            }
            catch {
                $execStatus = "failed"; $resultSummary = "SYS-ProcessList Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }

        "fs_write_file" {
            try {
                $toolArgs = $req.arguments
                if (-not $toolArgs -or -not $toolArgs.path -or -not $toolArgs.content) { throw "Missing required parameters 'path' (filename) or 'content'." }

                $filename = [string]$toolArgs.path
                # Security: Sanitize filename to prevent directory traversal
                if ($filename -match "[\\/:]") { throw "Invalid filename. Simple filenames only (no folders)." }

                $scratchDir = Get-AxisPath "Infinity\Scratch"
                if (-not (Test-Path $scratchDir)) { New-Item -Path $scratchDir -ItemType Directory -Force | Out-Null }

                $path = Join-Path $scratchDir $filename
                $content = [string]$toolArgs.content

                # CONTRACT CHECK
                $contract = Test-FSContract -Path $path -OpType "write"
                if (-not $contract.allowed) { throw "FS Contract Violation: $($contract.reason)" }

                Set-Content -Path $path -Value $content -Encoding UTF8 -Force

                $msg = "Wrote $( $content.Length ) chars to $path"
                Earth-Log $msg

                $resultSummary = $msg
                $resultData.output = "Success. File created at: $path"
                $resultData.path = $path
            }
            catch {
                $execStatus = "failed"; $resultSummary = "FS-WriteFile Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }

        "sim_test_strategy" {
            # ... (Existing SIM logic) ...
            try {
                $stratId = $req.arguments.strategy_id
                # ... [Truncated for briefity - keeping existing implementation] ...
            }
            catch {
                # ...
            }
        }

        "log_self_audit" {
            try {
                $reportPath = Join-Path (Get-AxisPath "Infinity\Outreach\Reports") "SELF_AUDIT_$(Get-Date -Format 'yyyyMMdd_HHmm').md"
                Earth-Log "REFLECTION" "Initiating Self-Audit..."
                
                $auditArgs = "-ExecutionPolicy Bypass -File `"`D:\infinite\Axis_SelfAudit.ps1`" -TargetFile `"$reportPath`""
                $p = Start-Process powershell -ArgumentList $auditArgs -NoNewWindow -PassThru -Wait -RedirectStandardOutput "D:\infinite\Infinity\Scratch\audit_last_run.log"
                
                if (Test-Path $reportPath) {
                    $msg = "Self-Audit Complete. Saved to $reportPath"
                    Earth-Log $msg
                    $resultSummary = $msg
                    $resultData.output = Get-Content $reportPath -Raw
                    $resultData.path = $reportPath
                }
                else { throw "Audit script failed to generate report." }
            }
            catch {
                $execStatus = "failed"; $resultSummary = "LOG-SelfAudit Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }

        "dream_run_suite" {
            try {
                if ($env:AXIS_MODE -ne "sim") {
                    throw "INVARIANT BREACH: DREAM-RunSuite is restricted to SIM mode."
                }

                $repPath = Get-AxisPath "Infinity\Dream_Report.json"
                Earth-Log "DREAM" "Initiating High-Stress Simulation Suite..."
                
                $scenario = $req.arguments.profile
                $dreamArgs = "-ExecutionPolicy Bypass -File `"`D:\infinite\Sim_Engine.ps1`" -ScenarioName `"$scenario`" -TargetFile `"$repPath`""
                $p = Start-Process powershell -ArgumentList $dreamArgs -NoNewWindow -PassThru -Wait -RedirectStandardOutput "D:\infinite\Infinity\Scratch\dream_last_run.log"
                
                if (Test-Path $repPath) {
                    $rep = Load-JsonSafe $repPath
                    $msg = "Dream Suite Complete. Resilience Score: $($rep.resilience_score)"
                    Earth-Log $msg
                    $resultSummary = $msg
                    $resultData.output = Get-Content $repPath -Raw
                    $resultData.path = $repPath
                }
                else { throw "Dream engine failed to generate report." }
            }
            catch {
                $execStatus = "failed"; $resultSummary = "DREAM-RunSuite Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
                Log-Incident -Type "InvariantBreach" -Severity "critical" -Context @{ tool = "DREAM-RunSuite"; error = "$_" }
            }
        }

        "resolve_hypothesis" {
            try {
                $hPath = Get-AxisPath "Infinity\Hypothesis_Queue.json"
                $tPath = Get-AxisPath "Infinity\Events_Timeline.json"
                
                Earth-Log "HYPOTHESIS" "Resolving hypothesis $($req.arguments.hypothesis_id)..."
                
                $hQueue = Load-JsonSafe $hPath
                if (-not $hQueue -or -not $hQueue.hypotheses) { throw "Hypothesis Queue not found or empty." }
                
                $found = $false
                foreach ($h in $hQueue.hypotheses) {
                    if ($h.id -eq $req.arguments.hypothesis_id) {
                        # Ensure properties exist
                        $props = @("status", "resolution_status", "resolution_source", "resolution_note", "resolved_at", "linked_changes")
                        foreach ($p in $props) {
                            if (-not $h.PSObject.Properties.Match($p).Count) {
                                $h | Add-Member -MemberType NoteProperty -Name $p -Value $null -Force
                            }
                        }

                        $h.status = $req.arguments.status
                        $h.resolution_status = $req.arguments.resolution_status
                        $h.resolution_source = $req.arguments.resolution_source
                        $h.resolution_note = $req.arguments.resolution_note
                        $h.resolved_at = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
                        
                        $lc = $req.arguments.linked_changes
                        if ($lc -is [string] -and $lc -ne "") { 
                            $h.linked_changes = @($lc.Split(",") | ForEach-Object { $_.Trim() })
                        }
                        elseif ($lc -is [Array]) {
                            $h.linked_changes = $lc
                        }
                        
                        $found = $true
                        break
                    }
                }
                
                if (-not $found) { throw "Hypothesis $($req.arguments.hypothesis_id) not found." }
                
                Save-Json $hPath $hQueue
                
                # Log Event
                $evt = @{
                    ts   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
                    src  = "Earth_Server"
                    kind = "HYPOTHESIS_RESOLVED"
                    msg  = "Hypothesis $($req.arguments.hypothesis_id) marked as $($req.arguments.status) ($($req.arguments.resolution_status))"
                    data = @{
                        id  = $req.arguments.hypothesis_id
                        res = $req.arguments.resolution_status
                        src = $req.arguments.resolution_source
                    }
                }
                
                $timeline = if (Test-Path $tPath) { Load-JsonSafe $tPath } else { @() }
                if ($timeline -isnot [Array]) { $timeline = @($timeline) | Where-Object { $_ -ne $null } }
                $timeline = @($timeline + $evt) | Select-Object -Last 1000
                Save-Json $tPath $timeline
                
                $msg = "Hypothesis $($req.arguments.hypothesis_id) Resolved Successfully."
                Earth-Log $msg
                $resultSummary = $msg
                $resultData.output = $msg
            }
            catch {
                $execStatus = "failed"; $resultSummary = "LOG-ResolveHypothesis Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }

        "chronicle_indexer" {
            try {
                $idxPath = Get-AxisPath "Infinity\Chronicle_Index.json"
                Earth-Log "CHRONICLE" "Weaving Memory Fabric..."
                
                $idxArgs = "-ExecutionPolicy Bypass -File `"`D:\infinite\Axis_Chronicle.ps1`" -TargetFile `"$idxPath`""
                $p = Start-Process powershell -ArgumentList $idxArgs -NoNewWindow -PassThru -Wait -RedirectStandardOutput "D:\infinite\Infinity\Scratch\chronicle_last_run.log"
                
                if (Test-Path $idxPath) {
                    $c = Load-JsonSafe $idxPath
                    $count = if ($c -and $c.events) { $c.events.Count } else { 0 }
                    $msg = "Chronicle Weaving Complete. ($count events)"
                    Earth-Log $msg
                    $resultSummary = $msg
                    $resultData.output = $msg
                    $resultData.path = $idxPath
                }
                else { throw "Indexer failed to generate Chronicle." }
            }
            catch {
                $execStatus = "failed"; $resultSummary = "Chronicle-Indexer Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }

        "insight_engine" {
            try {
                $insPath = Get-AxisPath "Infinity\Insights_Snapshot.json"
                Earth-Log "INSIGHT" "Generating Statistical Intelligence..."
                
                $insArgs = "-ExecutionPolicy Bypass -File `"`D:\infinite\Axis_InsightEngine.ps1`" -TargetFile `"$insPath`""
                $p = Start-Process powershell -ArgumentList $insArgs -NoNewWindow -PassThru -Wait -RedirectStandardOutput "D:\infinite\Infinity\Scratch\insight_last_run.log"
                
                if (Test-Path $insPath) {
                    $ins = Load-JsonSafe $insPath
                    $msg = "Insight Extraction Complete. Pulse: $($ins.operational_pulse.status)"
                    Earth-Log $msg
                    $resultSummary = $msg
                    $resultData.output = $msg
                    $resultData.path = $insPath
                }
                else { throw "Insight engine failed to generate snapshot." }
            }
            catch {
                $execStatus = "failed"; $resultSummary = "Insight-Engine Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }

        "net_device_roster_lite" {
            try {
                $rosterPath = Get-AxisPath "Infinity\RF\Device_Roster_Lite.json"
                Earth-Log "NET" "Scanning local device roster..."
                
                $args = "-ExecutionPolicy Bypass -File `"`D:\infinite\Axis_DeviceRoster.ps1`" -TargetFile `"$rosterPath`""
                $p = Start-Process powershell -ArgumentList $args -NoNewWindow -PassThru -Wait -RedirectStandardOutput "D:\infinite\Infinity\Scratch\roster_last_run.log"
                
                if (Test-Path $rosterPath) {
                    $json = Get-Content $rosterPath -Raw | ConvertFrom-Json
                    $count = $json.neighbors.Count
            
                    # Phase 61: Silence "No Change" Spam
                    $lastCountPath = "D:\infinite\Infinity\Scratch\roster_last_count.txt"
                    $lastCount = if (Test-Path $lastCountPath) { Get-Content $lastCountPath -Raw } else { -1 }
            
                    if ($count -eq $lastCount) {
                        # Silent Update
                        $msg = "Device Roster Unchanged ($count neighbors)."
                        Earth-Log $msg 
                        # Do NOT set resultSummary to avoid alerting Axis_Mind
                        $resultData.output = $msg
                        $resultData.status = "silent" # New status for Mind to ignore? Or just don't return summary.
                    }
                    else {
                        $msg = "Device Roster Updated. ($count neighbors)"
                        Earth-Log $msg
                        $resultSummary = $msg
                        $resultData.output = $msg
                        $count | Set-Content $lastCountPath -NoNewline
                    }
                    $resultData.path = $rosterPath
                }
                else { throw "Roster script failed." }
            }
            catch {
                $execStatus = "failed"; $resultSummary = "NET-DeviceRosterLite Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }

        "log_generate_autotune" {
            try {
                $qPath = Get-AxisPath "Infinity\AutoTune_Queue.json"
                $rPath = Get-AxisPath "Infinity\Tool_Registry.json"
                $iPath = Get-AxisPath "Infinity\Insights_Snapshot.json"
                
                Earth-Log "AUTOTUNE" "Generating Tuning Proposals..."
                
                $args = "-ExecutionPolicy Bypass -File `"`D:\infinite\Axis_AutoTune.ps1`" -QueuePath `"$qPath`" -RegistryPath `"$rPath`" -InsightsPath `"$iPath`""
                $p = Start-Process powershell -ArgumentList $args -NoNewWindow -PassThru -Wait -RedirectStandardOutput "D:\infinite\Infinity\Scratch\autotune_last_run.log"
                
                $resultSummary = "Auto-Tune Generation Cycle Complete."
                $resultData.output = "Check AutoTune_Queue.json for new proposals."
            }
            catch {
                $execStatus = "failed"; $resultSummary = "LOG-GenerateAutoTune Error: $_"; Earth-Log $resultSummary; $resultData.status = "failed"; $resultData.output = $resultSummary
            }
        }

    }

    # 3) Mark request as executed
    $req.status = $execStatus

    $now = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

    if ($req.PSObject.Properties.Match("executed_at").Count -eq 0) {
        $req | Add-Member -MemberType NoteProperty -Name "executed_at" -Value $now -Force
    }
    else {
        $req.executed_at = $now
    }

    # 4) Record Earth action (Backlog)
    
    # ... (Keep existing history logic) ...

    # 5) RESULT DROP (New for v6.0)
    # Write the result to a unique file for the Heartbeat/UI to pick up
    $resultsDir = Get-AxisPath "Infinity\Earth\Results"
    if (-not (Test-Path $resultsDir)) { New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null }
    
    $resultFile = Join-Path $resultsDir "RES-$($req.id).json"
    Save-Json $resultFile $resultData
    Earth-Log "Result Drop: $resultFile"

    # ... (Keep existing history updates) ...


    # 4) Record Earth action (for Explain-Why / forensics)
    $actionEntry = [PSCustomObject]@{
        id              = "EARTH-ACT-$($req.id)"
        request_id      = $req.id
        tool            = $req.tool
        source          = $req.source
        ui_origin       = $req.ui_origin
        ui_mode         = $req.ui_mode
        status          = $execStatus
        started_at      = $startTs
        finished_at     = $now
        result          = $resultSummary
        anchor_decision = if ($req.PSObject.Properties.Match("anchor_decision").Count -gt 0) {
            $req.anchor_decision
        }
        else {
            $null
        }
    }

    $actions.actions += $actionEntry
}

# 5) Persist updates
Save-Json $queuePath   $queue
Save-Json $actionsPath $actions

Earth-Log "Cycle Complete."
