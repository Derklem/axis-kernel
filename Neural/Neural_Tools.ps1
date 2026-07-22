
# ============================================================
# Neural Tools (Phase 64)
# ============================================================
# Core Logic for Neural Strategies
# ============================================================

if (-not $Script:InfinityRoot) { $Script:InfinityRoot = "D:\Infinite" }
$Script:NeuralSanityReportPath = Join-Path $Script:InfinityRoot "Infinity\Neural\Neural_Sanity_Report.json"

# Ensure Registry Helper Functions are loaded if not already
if (-not (Get-Command Get-NeuralChannelRegistry -ErrorAction SilentlyContinue)) {
    . "$Script:InfinityRoot\Infinity\Neural\Neural_Registry_Functions.ps1"
}

function NEURAL-HealthCheck {
    <#
    .SYNOPSIS
        Perform a read-only health check of enabled neural channels.
    #>
    param(
        [ValidateSet("read_only","full")]
        [string] $Mode = "read_only",
        [bool] $IncludeMetrics = $true,
        [string[]] $ChannelId
    )

    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_HEALTH" "Starting NEURAL-HealthCheck (Mode=$Mode)."
    }

    $channels = @()
    if ($ChannelId) {
        foreach ($id in $ChannelId) {
            $ch = Get-NeuralChannelById -ChannelId $id
            if ($ch) { $channels += $ch }
        }
    } else {
        $channels = Get-NeuralChannels -Status @("enabled")
    }

    if (-not $channels) { return }

    $now = (Get-Date).ToUniversalTime().ToString("o")

    foreach ($ch in $channels) {
        $id = $ch.channel_id
        $statusLabel = "ok"
        $errorMsg = $null
        
        try {
            switch ($ch.source_type) {
                "file" {
                    if (-not $ch.endpoint.path) { $statusLabel="error"; $errorMsg="No path" }
                    elseif (-not (Test-Path -LiteralPath $ch.endpoint.path)) { $statusLabel="error"; $errorMsg="File missing" }
                }
                "api" {
                    if (-not $ch.endpoint.url) { $statusLabel="error"; $errorMsg="No URL" }
                    if ($Mode -eq "full") {
                        # Stub for full check
                    }
                }
                default { $statusLabel="warning"; $errorMsg="Unknown type" }
            }
        } catch {
             $statusLabel="error"; $errorMsg=$_.Exception.Message
        }
        
        Update-NeuralChannelHealth -ChannelId $id -LastStatus $statusLabel -LastError $errorMsg -LastSeenUtc $now
        
        if ($IncludeMetrics) {
            $errRate = if ($statusLabel -eq "error") { 1.0 } else { 0.0 }
            Update-NeuralChannelMetrics -ChannelId $id -AvgEventsPerMin 0.0 -ErrorRate $errRate
        }
        
        if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
             Mind-Log "NEURAL_HEALTH" "Checked $id -> $statusLabel"
        }
    }
}

function NEURAL-IntakeSanity {
    <#
    .SYNOPSIS
        Scan neural intake sources for anomalies.
    #>
    param(
        [int] $WindowMinutes   = 30,
        [int] $MaxExpectedRate = 1000,
        [bool] $LogOnly        = $true,
        [string[]] $ChannelId
    )

    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_SANITY" "Starting NEURAL-IntakeSanity."
    }

    $channels = @()
    if ($ChannelId) {
         foreach ($id in $ChannelId) { 
             $ch = Get-NeuralChannelById -ChannelId $id; if ($ch) { $channels += $ch }
         }
    } else {
        $channels = (Get-NeuralChannels -Status @("enabled")) | Where-Object { $_.source_type -eq "file" }
    }

    if (-not $channels) { return }

    $now = (Get-Date).ToUniversalTime().ToString("o")
    $reportRows = @()

    foreach ($ch in $channels) {
        $id = $ch.channel_id
        $path = $ch.endpoint.path
        $anomalies = @(); $notes = @()
        $lineCount = 0; $sizeMB = 0.0; $parseErrors = 0; $parseTotal = 0
        
        if (-not $path -or -not (Test-Path $path)) {
            $anomalies += "missing"; $notes += "File missing path/content"
        } else {
            try {
                $item = Get-Item $path; $sizeMB = [math]::Round($item.Length/1MB, 3)
                $lines = Get-Content $path -Encoding UTF8
                $lineCount = $lines.Count
                
                # Format Sanity
                if ($ch.data_format -eq "jsonl" -and $lineCount -gt 0) {
                     $sampleSize = [Math]::Min(100, $lineCount)
                     $step = [Math]::Max([int]([Math]::Floor($lineCount/$sampleSize)), 1)
                     for ($i=0; $i -lt $lineCount -and $parseTotal -lt $sampleSize; $i+=$step) {
                         $parseTotal++
                         try { $null = $lines[$i] | ConvertFrom-Json } catch { $parseErrors++ }
                     }
                     if ($parseTotal -gt 0 -and ($parseErrors/$parseTotal) -gt 0.3) {
                         $anomalies += "format_errors"
                     }
                }
                
                # Retention/Rate checks
                if ($ch.retention_policy.max_mb -and $sizeMB -gt ($ch.retention_policy.max_mb * 1.5)) {
                    $anomalies += "retention_breach"
                }
            } catch { $anomalies += "io_error"; $notes += $_.Exception.Message }
        }
        
        $reportRows += [pscustomobject]@{
            channel_id = $id
            anomalies = $anomalies
            line_count = $lineCount
            size_mb = $sizeMB
            scan_time = $now
        }
        
        if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
             Mind-Log "NEURAL_SANITY" "$id -> $($anomalies -join ',')"
        }
    }
    
    $reportRows | ConvertTo-Json -Depth 5 | Set-Content $Script:NeuralSanityReportPath -Encoding UTF8
}

# ============================================================
# NEURAL-Quarantine (Proposal-Only)
# ============================================================

if (-not $Script:InfinityRoot) { $Script:InfinityRoot = "D:\Infinite" }
$Script:NeuralQuarantineProposalsPath = Join-Path $Script:InfinityRoot "Infinity\Neural\Neural_Quarantine_Proposals.json"

function NEURAL-Quarantine {
    <#
    .SYNOPSIS
        Analyze neural channels and propose quarantines.
    #>
    param(
        [ValidateSet("dry_run","propose_only")]
        [string] $Mode = "dry_run",
        [double] $ThresholdScore = 0.8,
        [string[]] $ChannelId
    )

    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_QUAR" "Starting NEURAL-Quarantine (Mode=$Mode, Threshold=$ThresholdScore)."
    }

    $registry = Get-NeuralChannelRegistry
    $channels = $registry.channels

    if ($ChannelId) {
        $channels = $channels | Where-Object { $ChannelId -contains $_.channel_id }
    } else {
        $channels = $channels | Where-Object { $_.status -eq "enabled" }
    }

    if (-not $channels) { return }

    # Load Sanity Report
    $sanityById = @{}
    if (Test-Path $Script:NeuralSanityReportPath) {
        try {
            $rep = Get-Content $Script:NeuralSanityReportPath -Raw | ConvertFrom-Json
            foreach ($r in $rep) { if($r.channel_id){$sanityById[$r.channel_id]=$r} }
        } catch {}
    }

    # Load Existing Proposals
    $proposalDoc = @{ version=1; proposals=@() }
    if (Test-Path $Script:NeuralQuarantineProposalsPath) {
        try {
             $p = Get-Content $Script:NeuralQuarantineProposalsPath -Raw | ConvertFrom-Json
             if($p.proposals){ $proposalDoc = $p }
        } catch {}
    }

    $newProposals = @()
    $now = (Get-Date).ToUniversalTime().ToString("o")

    foreach ($ch in $channels) {
        $id = $ch.channel_id
        $score = 0.0; $reasons = @()
        
        # Health Risk
        if ($ch.health.last_status -eq "error") { $score+=0.5; $reasons+="health_error" }
        if ($ch.health.last_status -eq "warning") { $score+=0.3; $reasons+="health_warning" }
        
        # Metrics Risk
        if ($ch.metrics.error_rate -gt 0.5) { $score+=0.3; $reasons+="high_error_rate" }
        
        # Sanity Risk
        if ($sanityById.ContainsKey($id)) {
            $anoms = $sanityById[$id].anomalies
            if ($anoms -contains "format_errors") { $score+=0.3; $reasons+="format_errors" }
            if ($anoms -contains "retention_breach") { $score+=0.2; $reasons+="retention_breach" }
            if ($anoms -contains "rate_excessive") { $score+=0.2; $reasons+="rate_excessive" }
        }
        
        if ($score -gt 1.0) { $score = 1.0 }
        
        if ($score -ge $ThresholdScore) {
             # Propose
             $pid = "NQ-$(Get-Date -Format 'yyyyMMddHHmmssfff')-$($id -replace '[^A-Za-z0-9]','')"
             $sug = if ($ch.trust_level -eq "external") { "disabled" } else { "quarantined" }
             
             $prop = [pscustomobject]@{
                 proposal_id = $pid
                 channel_id = $id
                 suggested_status = $sug
                 risk_score = [Math]::Round($score, 3)
                 reasons = $reasons
                 status = "pending"
                 created_at_utc = $now
                 created_by = "Axis"
             }
             $proposalDoc.proposals += $prop
             $newProposals += $prop
             
             if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
                  Mind-Log "NEURAL_QUAR" "Proposed $sug for $id (Score=$score)"
             }
        }
    }
    
    if ($newProposals.Count -gt 0) {
        $proposalDoc | ConvertTo-Json -Depth 10 | Set-Content $Script:NeuralQuarantineProposalsPath -Encoding UTF8
    }
}

function NEURAL-ApplyQuarantine {
    <#
    .SYNOPSIS
        Apply approved quarantine proposals.
    #>
    param(
        [ValidateSet("dry_run","execute")]
        [string] $Mode = "dry_run",
        [string[]] $ProposalId,
        [int] $MaxToApply
    )

    if (-not (Test-Path $Script:NeuralQuarantineProposalsPath)) { return }
    
    try {
        $json = Get-Content $Script:NeuralQuarantineProposalsPath -Raw -Encoding UTF8
        $doc = $json | ConvertFrom-Json
        $proposals = @($doc.proposals)
    } catch { return }
    
    $candidates = $proposals | Where-Object { $_.status -eq "approved" }
    
    if ($ProposalId) {
        $candidates = $candidates | Where-Object { $ProposalId -contains $_.proposal_id }
    }
    
    if ($MaxToApply -gt 0) { $candidates = $candidates | Select-Object -First $MaxToApply }
    
    $now = (Get-Date).ToUniversalTime().ToString("o")
    
    foreach ($p in $candidates) {
        if ($Mode -eq "dry_run") {
             if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
                 Mind-Log "NEURAL_APPLY" "Would apply: $($p.channel_id) -> $($p.suggested_status)"
             }
             continue
        }
        
        try {
            Set-NeuralChannelStatus -ChannelId $p.channel_id -Status $p.suggested_status
            $p.status = "applied"
            $p.applied_at_utc = $now
            $p.applied_by = "Axis"
            Mind-Log "NEURAL_APPLY" "Applied: $($p.channel_id) -> $($p.suggested_status)"
        } catch {
            $p.status = "failed"
            $p.apply_error = $_.Exception.Message
            $p.failed_at_utc = $now
        }
    }
    
    if ($Mode -eq "execute") {
        $doc.proposals = $proposals
        $doc | ConvertTo-Json -Depth 10 | Set-Content $Script:NeuralQuarantineProposalsPath -Encoding UTF8
    }
}

# ============================================================
# NEURAL-QuarantineReview
# ============================================================

if (-not $Script:InfinityRoot) { $Script:InfinityRoot = "D:\Infinite" }
$Script:NeuralQuarantineReviewPath = Join-Path $Script:InfinityRoot "Infinity\Neural\Neural_Quarantine_Review_Summary.json"

function NEURAL-QuarantineReview {
    <#
    .SYNOPSIS
        Summarize neural quarantine proposals.
    #>
    param(
        [ValidateSet("summary","pending_only")]
        [string] $Mode = "summary",
        [int] $MaxItems = 20,
        [bool] $IncludePending  = $true,
        [bool] $IncludeApproved = $true,
        [bool] $IncludeApplied  = $false
    )

    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_REVIEW" "Starting NEURAL-QuarantineReview (Mode=$Mode)."
    }

    if (-not (Test-Path $Script:NeuralQuarantineProposalsPath)) { return }

    try {
        $json = Get-Content $Script:NeuralQuarantineProposalsPath -Raw -Encoding UTF8
        $doc = $json | ConvertFrom-Json
        $proposals = @($doc.proposals)
    } catch { return }

    if (-not $proposals) { return }

    $now = (Get-Date).ToUniversalTime().ToString("o")

    # Counts
    $counts = @{}
    ($proposals | Group-Object status) | ForEach-Object { $counts[$_.Name] = $_.Count }

    # Filter
    $filtered = $proposals | Where-Object {
        ($IncludePending -and $_.status -eq "pending") -or
        ($IncludeApproved -and $_.status -eq "approved") -or
        ($IncludeApplied -and $_.status -eq "applied")
    }
    
    if ($Mode -eq "pending_only") { $filtered = $filtered | Where-Object { $_.status -eq "pending" } }
    
    # Top Risks
    $highRisk = $filtered | Sort-Object risk_score -Descending | Select-Object -First $MaxItems
    
    # Summary
    $summary = [pscustomobject]@{
        generated_at_utc = $now
        total_proposals = $proposals.Count
        counts_by_status = $counts
        high_risk_proposals = $highRisk
    }
    
    $summary | ConvertTo-Json -Depth 10 | Set-Content $Script:NeuralQuarantineReviewPath -Encoding UTF8
    
    # Log High Level
    $p=$counts['pending']; $a=$counts['approved']
    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_REVIEW" "Review: Pending=$p, Approved=$a"
    }
}

# ============================================================
# NEURAL-BuildUIInboxReview
# ============================================================

$Script:UIInboxNeuralReviewPath = Join-Path $Script:InfinityRoot "Infinity\UI\UI_Inbox_Neural_Review.json"

function NEURAL-BuildUIInboxReview {
    <#
    .SYNOPSIS
        Build UI Inbox Card for Neural Review.
    #>
    param(
        [int] $MaxCards = 20,
        [string[]] $IncludeStatuses = @("pending","approved")
    )
    
    $inboxDir = Split-Path $Script:UIInboxNeuralReviewPath
    if (-not (Test-Path $inboxDir)) { New-Item -ItemType Directory -Force -Path $inboxDir | Out-Null }
    
    # Load Proposals
    if (-not (Test-Path $Script:NeuralQuarantineProposalsPath)) { return }
    try {
         $p = Get-Content $Script:NeuralQuarantineProposalsPath -Raw | ConvertFrom-Json
         $proposals = @($p.proposals)
    } catch { return }
    
    if (-not $proposals) { return }
    
    $filtered = $proposals | Where-Object { $IncludeStatuses -contains $_.status }
    if (-not $filtered) { return }
    
    # Group by Channel
    $byChannel = $filtered | Group-Object channel_id
    $cards = @()
    
    foreach ($g in $byChannel) {
        $id = $g.Name
        $grp = $g.Group
        $maxRisk = ($grp | Measure-Object risk_score -Maximum).Maximum
        
        $sev = "low"
        if ($maxRisk -ge 0.8) { $sev="high" } elseif ($maxRisk -ge 0.5) { $sev="medium" }
        
        $primStat = "pending"
        # Logic matches user spec
        if (($grp | ? status -eq approved) -and -not ($grp | ? status -eq pending)) { $primStat="approved" }
        if (($grp | ? status -eq applied) -and -not ($grp | ? status -eq pending) -and -not ($grp | ? status -eq approved)) { $primStat="applied" }


        # Actions
        $actions = @()
        $seenActions = @{}

        function Add-UIAction {
            param($ActionId, $Label, $Kind, $PropId)
            $key = "$ActionId|$PropId"
            if ($seenActions.ContainsKey($key)) { return }
            $seenActions[$key] = $true
            
            $actions += [pscustomobject]@{
                action_id = $ActionId
                label = $Label
                kind = $Kind
                proposal_id = $PropId
            }
        }

        foreach ($item in $grp) {
            $pidStr = [string]$item.proposal_id # Ensure String
            if ($item.status -eq "pending") {
                Add-UIAction "approve_quarantine" "Approve" "primary" $pidStr
                Add-UIAction "reject_quarantine" "Reject" "secondary" $pidStr
            }
            elseif ($item.status -eq "approved") {
                Add-UIAction "apply_quarantine" "Apply" "primary" $pidStr
            }
        }
        Add-UIAction "view_details" "Details" "info" $null
        
        # Access local variable $actions from parent scope since function modifies it implicitly? 
        # No, PowerShell functions have scope. 
        # Better: Just use the logic inline or scoped correctly.
        # Inline for simplicity/reliability in this context:
        
        $actions = @()
        $seenActions = @{}
        
        foreach ($item in $grp) {
            $pidStr = [string]$item.proposal_id
            
            if ($item.status -eq "pending") {
                $k1 = "approve_quarantine|$pidStr"
                if (-not $seenActions[$k1]) {
                    $actions += @{ action_id="approve_quarantine"; label="Approve"; kind="primary"; proposal_id=$pidStr }
                    $seenActions[$k1]=$true
                }
                
                $k2 = "reject_quarantine|$pidStr"
                if (-not $seenActions[$k2]) {
                    $actions += @{ action_id="reject_quarantine"; label="Reject"; kind="secondary"; proposal_id=$pidStr }
                    $seenActions[$k2]=$true
                }
            }
            elseif ($item.status -eq "approved") {
                $k3 = "apply_quarantine|$pidStr"
                if (-not $seenActions[$k3]) {
                     $actions += @{ action_id="apply_quarantine"; label="Apply"; kind="primary"; proposal_id=$pidStr }
                     $seenActions[$k3]=$true
                }
            }
        }
        $actions += @{ action_id="view_details"; label="Details"; kind="info"; proposal_id=$null }

        
        $cards += [pscustomobject]@{
             card_id = "UI-NQ-" + ($id -replace "[^A-Za-z0-9]","")
             type = "neural_quarantine"
             channel_id = $id
             title = "Quarantine: $id"
             subtitle = "Risk $maxRisk ($primStat)"
             severity = $sev
             status = $primStat
             risk_score = $maxRisk
             source = "NEURAL-QuarantineReview"
             actions = $actions
        }
    }
    
    $doc = [pscustomobject]@{
        version = 1
        inbox_id = "UI-INBOX-NEURAL-REVIEW"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        cards = $cards | Sort-Object risk_score -Descending | Select-Object -First $MaxCards
    }
    
    $doc | ConvertTo-Json -Depth 10 | Set-Content $Script:UIInboxNeuralReviewPath -Encoding UTF8
    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_UI" "Built UI Inbox ($($cards.Count) cards)"
    }
}

# ============================================================
# NEURAL-Intake-Heartbeat
# ============================================================

$Script:NeuralEventIndexPath = Join-Path $Script:InfinityRoot "Infinity\Neural\Neural_Event_Index.json"
$Script:HeartbeatMetricsPath = Join-Path $Script:InfinityRoot "Infinity\Neural\Heartbeat_Metrics.json"

function NEURAL-Intake-Heartbeat {
    <#
    .SYNOPSIS
        Ingest System Heartbeat logs into Metrics and Event Index.
    #>
    param(
        [ValidateSet("read_only","ingest")]
        [string] $Mode = "read_only",
        [int] $MaxLines = 100
    )

    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_INTAKE" "Starting Heartbeat Intake (Mode=$Mode)."
    }

    # 1. Resolve Channel & Path
    $ch = Get-NeuralChannelById -ChannelId "NEURAL-SYS-HEARTBEAT-001"
    if (-not $ch -or $ch.status -ne "enabled") { return }
    
    $path = $ch.endpoint.path
    if (-not (Test-Path $path)) { return }
    
    # 2. Read Tail
    try {
        $lines = Get-Content -Path $path -Tail $MaxLines -Encoding UTF8
    } catch { return }

    if (-not $lines) { return }

    # 3. Parse & Analyze
    $validCount = 0
    $lastValid = $null
    
    # Simple rolling stats
    $sumLoad = 0.0
    $countLoad = 0
    
    foreach ($line in $lines) {
        if (-not $line) { continue }
        try {
            $obj = $line | ConvertFrom-Json
            if ($obj.timestamp -and $obj.bpm) {
                $lastValid = $obj
                $validCount++
                if ($obj.load) { $sumLoad += [double]$obj.load; $countLoad++ }
            }
        } catch {}
    }

    if ($validCount -eq 0) { return }

    # 4. Update Metrics (if ingest)
    if ($Mode -eq "ingest") {
        $now = (Get-Date).ToUniversalTime().ToString("o")
        
        # Load Metrics
        $metrics = @{ version=1; history=@() }
        if (Test-Path $Script:HeartbeatMetricsPath) {
            try { $metrics = Get-Content $Script:HeartbeatMetricsPath -Raw | ConvertFrom-Json } catch {}
        }
        
        # Update Current
        $metrics.last_updated_utc = $now
        $metrics.current_bpm = $lastValid.bpm
        $metrics.status = if ($lastValid.status) { $lastValid.status } else { "ok" }
        
        if ($countLoad -gt 0) {
             $metrics.load_avg_1m = [Math]::Round($sumLoad / $countLoad, 2)
        }
        
        # Append to History (Keep last 50 points)
        $pt = @{ ts=$now; bpm=$metrics.current_bpm; load=$metrics.load_avg_1m }
        $metrics.history += $pt
        if ($metrics.history.Count -gt 50) {
            $metrics.history = $metrics.history | Select-Object -Last 50
        }
        
        $metrics | ConvertTo-Json -Depth 5 | Set-Content $Script:HeartbeatMetricsPath -Encoding UTF8
        
        # 5. Emit Events (e.g. Status Change or High Load)
        # Stub logic: If status != 'ok', emit event
        if ($metrics.status -ne "ok") {
            $evt = @{
                event_id = "NEURAL-EVT-" + (Get-Date -Format "yyyyMMddHHmmssfff")
                type = "heartbeat_status_change"
                source = "NEURAL-Intake-Heartbeat"
                timestamp = $now
                info = @{ status = $metrics.status; bpm = $metrics.current_bpm }
                severity = "medium"
            }
            
            # Load Index
            $index = @{ version=1; events=@() }
            if (Test-Path $Script:NeuralEventIndexPath) {
                 try { $index = Get-Content $Script:NeuralEventIndexPath -Raw | ConvertFrom-Json } catch {}
            }
            
            # Dedup check (very crude, assume time separation)
            $index.events += $evt
            # Prune index (keep last 100)
            if ($index.events.Count -gt 100) { $index.events = $index.events | Select-Object -Last 100 }
            
            $index | ConvertTo-Json -Depth 10 | Set-Content $Script:NeuralEventIndexPath -Encoding UTF8
            Mind-Log "NEURAL_INTAKE" "Emitted Event: $($evt.type) -> $($metrics.status)"
        }
        

        Mind-Log "NEURAL_INTAKE" "Ingested $validCount lines. BPM=$($metrics.current_bpm)"
    }
}

# ============================================================
# NEURAL-Intake-Weather
# ============================================================

$Script:WeatherMetricsPath = Join-Path $Script:InfinityRoot "Infinity\Neural\Weather_Metrics.json"

function NEURAL-Intake-Weather {
    <#
    .SYNOPSIS
        Ingest external weather data from the Weather raw log into metrics and events.
    #>
    param(
        [string] $ChannelId = "NEURAL-EXT-WEATHER-001",
        [int]    $HistoryLimit = 200
    )

    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_WEATHER" "Starting NEURAL-Intake-Weather (Channel=$ChannelId)."
    }

    $ch = Get-NeuralChannelById -ChannelId $ChannelId
    if (-not $ch) { return }

    $path = $ch.endpoint.path
    if (-not $path -or -not (Test-Path -LiteralPath $path)) {
        if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
            Mind-Log "NEURAL_WEATHER" "Raw log missing for $ChannelId at $path"
        }
        return
    }

    # Load all events (jsonl)
    $lines = Get-Content -LiteralPath $path -Encoding UTF8
    if (-not $lines -or $lines.Count -eq 0) { return }

    $events = @()
    foreach ($line in $lines) {
        if (-not $line.Trim()) { continue }
        try {
            $e = $line | ConvertFrom-Json
            if ($e.timestamp_utc) { $events += $e }
        } catch { }
    }
    if (-not $events -or $events.Count -eq 0) { return }

    # Take most recent event
    $latest = $events | Sort-Object { [DateTime]::Parse($_.timestamp_utc) } -Descending | Select-Object -First 1

    $now       = (Get-Date).ToUniversalTime().ToString("o")
    $location  = $latest.location
    $temp      = [double]$latest.temp_c
    $cond      = [string]$latest.condition
    $humidity  = if ($latest.humidity -ne $null) { [int]$latest.humidity } else { $null }
    $wind      = if ($latest.wind_kph -ne $null) { [double]$latest.wind_kph } else { $null }
    $precip    = if ($latest.precip_mm -ne $null) { [double]$latest.precip_mm } else { $null }

    # Load existing metrics
    $metrics = @{
        version           = 1
        metric_id         = "METRIC-WEATHER-001"
        last_updated_utc  = $null
        location          = "UNKNOWN"
        current_temp_c    = $null
        current_condition = $null
        current_humidity  = $null
        current_wind_kph  = $null
        current_precip_mm = $null
        status            = "unknown"
        alerts            = @()
        history           = @()
    }

    $oldTemp = $null
    $oldCond = $null

    if (Test-Path -LiteralPath $Script:WeatherMetricsPath) {
        try {
            $metrics = Get-Content -LiteralPath $Script:WeatherMetricsPath -Raw | ConvertFrom-Json
            $oldTemp = $metrics.current_temp_c
            $oldCond = $metrics.current_condition
        } catch { }
    }

    if (-not $metrics.history) { $metrics.history = @() }
    if (-not $metrics.alerts)  { $metrics.alerts  = @() }

    # Append to history
    $histEntry = [pscustomobject]@{
        timestamp_utc = $latest.timestamp_utc
        temp_c        = $temp
        condition     = $cond
        humidity      = $humidity
        wind_kph      = $wind
        precip_mm     = $precip
    }
    $metrics.history += $histEntry
    if ($metrics.history.Count -gt $HistoryLimit) {
        $metrics.history = $metrics.history | Select-Object -Last $HistoryLimit
    }

    # Compute status
    $status = "ok"
    $alerts = @()

    if ($cond -match "Storm|Thunder|Tornado|Hurricane|Snow") {
        $status = "alert"
        $alerts += "severe_condition:$cond"
    }

    if ($temp -lt -10 -or $temp -gt 40) {
        $status = "alert"
        $alerts += "extreme_temp:$temp"
    }

    # Detect significant change (~5.0 C)
    if ($oldTemp -ne $null) {
        $tempDelta = [math]::Abs([double]$temp - [double]$oldTemp)
        if ($tempDelta -ge 5.0) {
            $alerts += "temp_jump:$tempDelta"
        }
    }

    if ($oldCond -and $oldCond -ne $cond) {
        $alerts += "condition_change:$oldCond->$cond"
    }

    $metrics.last_updated_utc  = $latest.timestamp_utc
    $metrics.location          = $location
    $metrics.current_temp_c    = $temp
    $metrics.current_condition = $cond
    $metrics.current_humidity  = $humidity
    $metrics.current_wind_kph  = $wind
    $metrics.current_precip_mm = $precip
    $metrics.status            = $status
    $metrics.alerts            = $alerts

    # Persist metrics
    $metrics | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:WeatherMetricsPath -Encoding UTF8

    # Emit events into Neural_Event_Index for alerts
    if ($alerts.Count -gt 0) {
        $indexDoc = @{ version=1; index_id="NEURAL-IDX-2026-001"; events=@() }

        if (Test-Path -LiteralPath $Script:NeuralEventIndexPath) {
            try {
                $indexDoc = Get-Content -LiteralPath $Script:NeuralEventIndexPath -Raw | ConvertFrom-Json
                if (-not $indexDoc.events) { $indexDoc.events = @() }
            } catch { }
        }

        $evt = [pscustomobject]@{
            timestamp_utc = $latest.timestamp_utc
            channel_id    = $ChannelId
            type          = "weather_alert"
            temp_c        = $temp
            condition     = $cond
            alerts        = $alerts
            source        = "NEURAL-Intake-Weather"
        }

        $indexDoc.events += $evt
        if ($indexDoc.events.Count -gt 2000) {
            $indexDoc.events = $indexDoc.events | Select-Object -Last 2000
        }

        $indexDoc | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:NeuralEventIndexPath -Encoding UTF8
    }


    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_WEATHER" "Ingested weather snapshot for $location; temp=$temp, cond=$cond"
    }
}

# ============================================================
# NEURAL-Intake-RouterTelemetry
# ============================================================

$Script:RouterMetricsPath = Join-Path $Script:InfinityRoot "Infinity\Neural\Router_Metrics.json"

function NEURAL-Intake-RouterTelemetry {
    <#
    .SYNOPSIS
        Ingest router telemetry into Router_Metrics.json and Neural_Event_Index.json.
    #>
    param(
        [string] $ChannelId = "NEURAL-NET-ROUTER-001",
        [int]    $HistoryLimit = 200
    )

    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_ROUTER" "Starting NEURAL-Intake-RouterTelemetry (Channel=$ChannelId)."
    }

    $ch = Get-NeuralChannelById -ChannelId $ChannelId
    if (-not $ch) { return }

    $path = $ch.endpoint.path
    if (-not $path -or -not (Test-Path -LiteralPath $path)) {
        if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
            Mind-Log "NEURAL_ROUTER" "Raw log missing for $ChannelId at $path"
        }
        return
    }

    $lines = Get-Content -LiteralPath $path -Encoding UTF8
    if (-not $lines -or $lines.Count -eq 0) { return }

    $events = @()
    foreach ($line in $lines) {
        if (-not $line.Trim()) { continue }
        try {
            $e = $line | ConvertFrom-Json
            if ($e.timestamp_utc) { $events += $e }
        } catch { }
    }
    if (-not $events -or $events.Count -eq 0) { return }

    $latest = $events | Sort-Object { [DateTime]::Parse($_.timestamp_utc) } -Descending | Select-Object -First 1

    $now      = (Get-Date).ToUniversalTime().ToString("o")
    $hostname = $latest.hostname
    $model    = $latest.model
    $wanIp    = $latest.wan_ip

    $rx       = [double]$latest.rx_mbps
    $tx       = [double]$latest.tx_mbps
    $clients  = [int]$latest.active_clients
    $wanUp    = [bool]$latest.wan_up

    $authFail = if ($latest.auth_failures_5m -ne $null) { [int]$latest.auth_failures_5m } else { 0 }
    $dhcpConf = if ($latest.dhcp_conflicts_5m -ne $null) { [int]$latest.dhcp_conflicts_5m } else { 0 }

    # Load existing metrics
    $metrics = @{
        version          = 1
        metric_id        = "METRIC-ROUTER-001"
        last_updated_utc = $null
        identity         = @{ hostname = $null; model = $null; wan_ip = $null }
        traffic          = @{ rx_mbps = 0.0; tx_mbps = 0.0; active_clients = 0 }
        errors           = @{ wan_down_events_24h = 0; auth_failures_24h = 0; dhcp_conflicts_24h = 0 }
        status           = "unknown"
        alerts           = @()
        history          = @()
    }

    $oldClients = $null
    $oldWanUp   = $null

    if (Test-Path -LiteralPath $Script:RouterMetricsPath) {
        try {
            $metrics   = Get-Content -LiteralPath $Script:RouterMetricsPath -Raw | ConvertFrom-Json
            $oldClients = $metrics.traffic.active_clients
            $oldWanUp   = $metrics.history | Sort-Object timestamp_utc -Descending | Select-Object -First 1 | ForEach-Object { $_.wan_up }
        } catch { }
    }

    if (-not $metrics.history) { $metrics.history = @() }
    if (-not $metrics.alerts)  { $metrics.alerts  = @() }

    $histEntry = [pscustomobject]@{
        timestamp_utc   = $latest.timestamp_utc
        rx_mbps         = $rx
        tx_mbps         = $tx
        active_clients  = $clients
        wan_up          = $wanUp
        auth_failures   = $authFail
        dhcp_conflicts  = $dhcpConf
    }
    $metrics.history += $histEntry
    if ($metrics.history.Count -gt $HistoryLimit) {
        $metrics.history = $metrics.history | Select-Object -Last $HistoryLimit
    }

    # Status & alerts
    $status = "ok"
    $alerts = @()

    if (-not $wanUp) {
        $status = "alert"
        $alerts += "wan_down"
    }

    if ($authFail -gt 0) {
        $alerts += "auth_failures_5m:$authFail"
    }

    if ($dhcpConf -gt 0) {
        $alerts += "dhcp_conflicts_5m:$dhcpConf"
    }

    if ($oldClients -ne $null) {
        $deltaClients = [math]::Abs($clients - [int]$oldClients)
        if ($deltaClients -ge 10) {
            $alerts += "client_jump:$deltaClients"
        }
    }

    $metrics.last_updated_utc           = $latest.timestamp_utc
    $metrics.identity.hostname          = $hostname
    $metrics.identity.model             = $model
    $metrics.identity.wan_ip            = $wanIp
    $metrics.traffic.rx_mbps            = $rx
    $metrics.traffic.tx_mbps            = $tx
    $metrics.traffic.active_clients     = $clients
    $metrics.status                     = $status
    $metrics.alerts                     = $alerts

    $metrics | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:RouterMetricsPath -Encoding UTF8

    # Emit security / router events when alerts are present
    if ($alerts.Count -gt 0) {
        $indexDoc = @{ version=1; index_id="NEURAL-IDX-2026-001"; events=@() }

        if (Test-Path -LiteralPath $Script:NeuralEventIndexPath) {
            try {
                $indexDoc = Get-Content -LiteralPath $Script:NeuralEventIndexPath -Raw | ConvertFrom-Json
                if (-not $indexDoc.events) { $indexDoc.events = @() }
            } catch { }
        }

        $evt = [pscustomobject]@{
            timestamp_utc = $latest.timestamp_utc
            channel_id    = $ChannelId
            type          = "router_anomaly"
            rx_mbps       = $rx
            tx_mbps       = $tx
            active_clients = $clients
            alerts        = $alerts
            source        = "NEURAL-Intake-RouterTelemetry"
        }

        $indexDoc.events += $evt
        if ($indexDoc.events.Count -gt 2000) {
            $indexDoc.events = $indexDoc.events | Select-Object -Last 2000
        }

        $indexDoc | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:NeuralEventIndexPath -Encoding UTF8
    }

    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_ROUTER" "Ingested router snapshot; clients=$clients, wan_up=$wanUp, alerts=$($alerts -join ',')"
    }
}

# ============================================================
# SEC-NetSignalSummary
# ============================================================

function SEC-NetSignalSummary {
    <#
    .SYNOPSIS
        Summarize network anomalies for review.
    #>
    param(
        [int] $LookbackHours = 24
    )
    
    Mind-Log "SEC_NET" "Generating Security Summary (Lookback: ${LookbackHours}h)"
    
    if (-not (Test-Path $Script:NeuralEventIndexPath)) { return "No events index." }
    
    try {
        $idx = Get-Content $Script:NeuralEventIndexPath -Raw | ConvertFrom-Json
        $cutoff = (Get-Date).AddHours(-$LookbackHours).ToUniversalTime()
        
        $anomalies = $idx.events | Where-Object { 
            ($_.type -eq "router_anomaly" -or $_.type -eq "security_signal") -and 
            ([DateTime]$_.timestamp_utc -gt $cutoff) 
        }
        
        if ($anomalies) {
             # Group by alert type
             $grouped = $anomalies | Group-Object type
             $report = "Security/Network Summary (Last ${LookbackHours}h):`n"
             foreach ($g in $grouped) {
                 $report += "- $($g.Name): $($g.Count) events`n"
             }
             
             # Log to UI Inbox (Mock) or Symbiosis Journal
             # For now, just return report string
             return $report
        } else {
             return "No anomalies detected in last ${LookbackHours} hours."
        }
    } catch {
        return "Error gathering summary: $_"
    }
}

# ============================================================
# NEURAL-Intake-Retina
# ============================================================

$Script:RetinaMetricsPath = Join-Path $Script:InfinityRoot "Infinity\Neural\Retina_Metrics.json"

function NEURAL-Intake-Retina {
    <#
    .SYNOPSIS
        Ingest retina metadata from Retina_Raw.log into Retina_Metrics.json and Neural_Event_Index.json.
    #>
    param(
        [string] $ChannelId    = "NEURAL-VIS-RETINA-001",
        [int]    $HistoryLimit = 500
    )

    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_RETINA" "Starting NEURAL-Intake-Retina (Channel=$ChannelId)."
    }

    $ch = Get-NeuralChannelById -ChannelId $ChannelId
    if (-not $ch) { return }

    $path = $ch.endpoint.path
    if (-not $path -or -not (Test-Path -LiteralPath $path)) {
        if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
            Mind-Log "NEURAL_RETINA" "Raw log missing for $ChannelId at $path"
        }
        return
    }

    $lines = Get-Content -LiteralPath $path -Encoding UTF8
    if (-not $lines -or $lines.Count -eq 0) { return }

    $events = @()
    foreach ($line in $lines) {
        if (-not $line.Trim()) { continue }
        try {
            $e = $line | ConvertFrom-Json
            if ($e.timestamp_utc -and $e.path) { $events += $e }
        } catch { }
    }
    if (-not $events -or $events.Count -eq 0) { return }

    # Take the latest frame
    $latest = $events | Sort-Object { [DateTime]::Parse($_.timestamp_utc) } -Descending | Select-Object -First 1

    $now     = (Get-Date).ToUniversalTime().ToString("o")
    $src     = [string]$latest.source
    $frame   = [string]$latest.path
    $bytes   = if ($latest.bytes -ne $null) { [long]$latest.bytes } else { 0 }
    $tags    = if ($latest.tags) { @($latest.tags) } else { @() }
    $hl      = [bool]$latest.highlight

    # Load existing metrics
    $metrics = @{
        version           = 1
        metric_id         = "METRIC-RETINA-001"
        last_updated_utc  = $null
        frames_total      = 0
        frames_highlighted= 0
        last_source       = $null
        last_frame_path   = $null
        last_frame_tags   = @()
        status            = "unknown"
        alerts            = @()
        history           = @()
    }

    if (Test-Path -LiteralPath $Script:RetinaMetricsPath) {
        try {
            $metrics = Get-Content -LiteralPath $Script:RetinaMetricsPath -Raw | ConvertFrom-Json
        } catch { }
    }

    if (-not $metrics.history) { $metrics.history = @() }
    if (-not $metrics.alerts)  { $metrics.alerts  = @() }

    # Update counters
    $metrics.frames_total = [int]$metrics.frames_total + 1
    if ($hl) { $metrics.frames_highlighted = [int]$metrics.frames_highlighted + 1 }

    $metrics.last_updated_utc = $latest.timestamp_utc
    $metrics.last_source      = $src
    $metrics.last_frame_path  = $frame
    $metrics.last_frame_tags  = $tags

    # History
    $histEntry = [pscustomobject]@{
        timestamp_utc = $latest.timestamp_utc
        source        = $src
        bytes         = $bytes
        tags          = $tags
        highlight     = $hl
    }
    $metrics.history += $histEntry
    if ($metrics.history.Count -gt $HistoryLimit) {
        $metrics.history = $metrics.history | Select-Object -Last $HistoryLimit
    }

    # Status / alerts (purely informational, no actions)
    $alerts = @()

    if ($hl) {
        $alerts += "highlight_frame"
    }

    if ($bytes -gt 10MB) {
        $alerts += "large_frame_bytes:$bytes"
    }

    $metrics.status  = if ($alerts.Count -gt 0) { "active" } else { "ok" }
    $metrics.alerts  = $alerts

    # Persist metrics
    $metrics | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:RetinaMetricsPath -Encoding UTF8

    # Emit events into Neural_Event_Index for highlighted frames only
    if ($hl) {
        $indexDoc = @{ version=1; index_id="NEURAL-IDX-2026-001"; events=@() }

        if (Test-Path -LiteralPath $Script:NeuralEventIndexPath) {
            try {
                $indexDoc = Get-Content -LiteralPath $Script:NeuralEventIndexPath -Raw | ConvertFrom-Json
                if (-not $indexDoc.events) { $indexDoc.events = @() }
            } catch { }
        }

        $evt = [pscustomobject]@{
            timestamp_utc = $latest.timestamp_utc
            channel_id    = $ChannelId
            type          = "retina_frame"
            path          = $frame
            source        = $src
            tags          = $tags
            alerts        = $alerts
            bytes         = $bytes
            highlight     = $hl
            source_tool   = "NEURAL-Intake-Retina"
        }

        $indexDoc.events += $evt
        if ($indexDoc.events.Count -gt 2000) {
            $indexDoc.events = $indexDoc.events | Select-Object -Last 2000
        }

        $indexDoc | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:NeuralEventIndexPath -Encoding UTF8
    }

    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_RETINA" "Ingested retina frame; source=$src, highlight=$hl, alerts=$($alerts -join ',')"
    }
}

# Load Shadow Tools if available
if (Test-Path "$Script:InfinityRoot\Infinity\Shadow\Shadow_Tools.ps1") {
    . "$Script:InfinityRoot\Infinity\Shadow\Shadow_Tools.ps1"
}






