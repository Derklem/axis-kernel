
# Axis_Dashboard.ps1
# Phase 71: Axis Dashboard & Haptic Bus
# Aggregates system state into UI-ready JSONs.

$Script:InfinityRoot            = "D:\Infinite"
$Script:HeartbeatMetricsPath    = Join-Path $Script:InfinityRoot "Infinity\Neural\Heartbeat_Metrics.json"
$Script:WeatherMetricsPath      = Join-Path $Script:InfinityRoot "Infinity\Neural\Weather_Metrics.json"
$Script:RouterMetricsPath       = Join-Path $Script:InfinityRoot "Infinity\Neural\Router_Metrics.json"
$Script:RetinaMetricsPath       = Join-Path $Script:InfinityRoot "Infinity\Neural\Retina_Metrics.json"
$Script:ShadowRiskIndexPath     = Join-Path $Script:InfinityRoot "Infinity\Shadow\Shadow_Risk_Index.json"
$Script:SymbiosisJournalPath    = Join-Path $Script:InfinityRoot "Infinity\Memory\Symbiosis_Journal.json" # Corrected path
$Script:NeuralQuarantinePath    = Join-Path $Script:InfinityRoot "Infinity\Neural\Neural_Quarantine_Proposals.json"
$Script:DashboardStatePath      = Join-Path $Script:InfinityRoot "Infinity\UI\Dashboard_State.json"
$Script:HapticAlertBusPath      = Join-Path $Script:InfinityRoot "Infinity\UI\Haptic_Alert_Bus.json"
$Script:UIInboxDashboardPath    = Join-Path $Script:InfinityRoot "Infinity\UI\UI_Inbox_Dashboard.json"
$Script:ShadowBiasFunctionsPath = Join-Path $Script:InfinityRoot "Infinity\Shadow\Shadow_Bias_Functions.ps1"

# Load Bias Functions (Phase 72)
if (Test-Path $Script:ShadowBiasFunctionsPath) { . $Script:ShadowBiasFunctionsPath }

# Load Anchor Functions (Phase 80)
if (Test-Path (Join-Path $Script:InfinityRoot "Infinity\Anchor\Axis_Anchor.ps1")) {
    . (Join-Path $Script:InfinityRoot "Infinity\Anchor\Axis_Anchor.ps1")
}

# Load Curriculum (Phase 81)
if (Test-Path (Join-Path $Script:InfinityRoot "Infinity\Skills\Axis_Curriculum.ps1")) {
    . (Join-Path $Script:InfinityRoot "Infinity\Skills\Axis_Curriculum.ps1")
}

# Load Autonomy Gate (Phase 82)
if (Test-Path (Join-Path $Script:InfinityRoot "Axis_AutonomyGate.ps1")) {
    . (Join-Path $Script:InfinityRoot "Axis_AutonomyGate.ps1")
}

# Ensure UI Dir
$uiDir = Join-Path $Script:InfinityRoot "Infinity\UI"
if (-not (Test-Path $uiDir)) { New-Item -ItemType Directory -Path $uiDir -Force | Out-Null }

function Load-JsonSafe {
    param([string]$Path, $Fallback)

    if (-not (Test-Path -LiteralPath $Path)) { return $Fallback }
    try {
        return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
    } catch {
        return $Fallback
    }
}

function DASH-BuildDashboardState {
    <#
    .SYNOPSIS
        Build a unified dashboard snapshot from metrics and shadow.
    #>
    param()

    $now = (Get-Date).ToUniversalTime().ToString("o")

    # 1. Load each metrics file
    $hb = Load-JsonSafe -Path $Script:HeartbeatMetricsPath -Fallback @{
        status            = "unknown"
        current_bpm       = 0
        load_avg_1m       = 0.0
        history           = @()
        last_updated_utc  = $null
    }

    $w = Load-JsonSafe -Path $Script:WeatherMetricsPath -Fallback @{
        status            = "unknown"
        location          = "UNKNOWN"
        current_temp_c    = $null
        current_condition = $null
        alerts            = @()
        last_updated_utc  = $null
    }

    $r = Load-JsonSafe -Path $Script:RouterMetricsPath -Fallback @{
        status            = "unknown"
        identity          = @{ hostname=$null; model=$null; wan_ip=$null }
        traffic           = @{ rx_mbps=0.0; tx_mbps=0.0; active_clients=0 }
        alerts            = @()
    }

    $ret = Load-JsonSafe -Path $Script:RetinaMetricsPath -Fallback @{
        status             = "unknown"
        frames_total       = 0
        frames_highlighted = 0
        last_source        = $null
        last_frame_path    = $null
        last_frame_tags    = @()
        alerts             = @()
    }

    $shadow = Load-JsonSafe -Path $Script:ShadowRiskIndexPath -Fallback @{
        summary = @{
            global_risk_score = 0.0
            bands = @{
                system      = 0.0
                network     = 0.0
                environment = 0.0
                visual      = 0.0
            }
        }
        last_updated_utc = $null
    }

    $sym = Load-JsonSafe -Path $Script:SymbiosisJournalPath -Fallback @{
        journal_entries = @()
    }
    # Handle schema variance (some journals use 'entries', some 'journal_entries')
    if ($sym.entries) { $entries = $sym.entries } 
    elseif ($sym.journal_entries) { $entries = $sym.journal_entries }
    else { $entries = @() }

    $nq = Load-JsonSafe -Path $Script:NeuralQuarantinePath -Fallback @{
        proposals = @()
    }

    # 2. Derive high-level slices

    # Heartbeat trend
    $trend = @()
    if ($hb.history -and $hb.history.Count -gt 0) {
        $recent = $hb.history | Select-Object -Last 5
        $trend = $recent | ForEach-Object { $_.bpm }
    }

    $heartbeatView = @{
        status        = $hb.status
        bpm           = $hb.current_bpm
        load_avg_1m   = $hb.load_avg_1m
        trend_bpm     = $trend
        last_updated  = $hb.last_updated_utc
    }

    # Environment
    $envView = @{
        status       = $w.status
        location     = $w.location
        temp_c       = $w.current_temp_c
        condition    = $w.current_condition
        alerts       = $w.alerts
        last_updated = $w.last_updated_utc
    }

    # Router
    $routerView = @{
        status          = $r.status
        hostname        = $r.identity.hostname
        wan_ip          = $r.identity.wan_ip
        active_clients  = $r.traffic.active_clients
        rx_mbps         = $r.traffic.rx_mbps
        tx_mbps         = $r.traffic.tx_mbps
        alerts          = $r.alerts
        last_updated    = $r.last_updated_utc
    }

    # Retina
    $retinaView = @{
        status             = $ret.status
        frames_total       = $ret.frames_total
        frames_highlighted = $ret.frames_highlighted
        last_source        = $ret.last_source
        last_frame_path    = $ret.last_frame_path
        last_frame_tags    = $ret.last_frame_tags
        alerts             = $ret.alerts
        last_updated       = $ret.last_updated_utc
    }

    # Shadow
    $shadowSummary = $shadow.summary
    $shadowView = @{
        global_risk_score = $shadowSummary.global_risk_score
        bands             = $shadowSummary.bands
        last_updated_utc  = $shadow.last_updated_utc
    }

    # Quarantine counts
    $pending  = ($nq.proposals | Where-Object { $_.status -eq "pending" }).Count
    $approved = ($nq.proposals | Where-Object { $_.status -eq "approved" }).Count
    $applied  = ($nq.proposals | Where-Object { $_.status -eq "applied" }).Count

    $nqView = @{
        pending  = $pending
        approved = $approved
        applied  = $applied
    }

    # Symbiosis preview
    $lastEntry = $null
    if ($entries.Count -gt 0) {
        $lastEntry = $entries | Sort-Object timestamp | Select-Object -Last 1
    }

    $symPreview = @{
        last_entry_ts_utc = if ($lastEntry) { $lastEntry.timestamp } else { $null }
        last_entry_id     = if ($lastEntry) { $lastEntry.id } else { $null }
        last_entry_tags   = if ($lastEntry -and $lastEntry.tags) { $lastEntry.tags } else { @() }
        preview           = if ($lastEntry -and $lastEntry.content) {
                                ($lastEntry.content -split "`n" | Select-Object -First 2) -join " "
                            } else {
                                $null
                            }
    }

    # Phase 72: Bias State
    $biasView = $null
    if (Get-Command Get-ShadowBiasState -ErrorAction SilentlyContinue) {
        $biasRaw = Get-ShadowBiasState
        $biasView = @{
            global_mode = $biasRaw.global_mode
            band_modes  = $biasRaw.band_modes
            profile_id  = $biasRaw.profile_id
        }
        }
    }

    # Phase 80: Anchor Integration
    $anchorPending = 0
    if (Get-Command ANCHOR-GetPendingReviewCount -ErrorAction SilentlyContinue) {
        $anchorPending = ANCHOR-GetPendingReviewCount
    }
    $anchorView = @{
        pending_reviews = $anchorPending
    }

    # Phase 81: Curriculum State
    $curricPending = 0
    if (Get-Command CURRIC-GetTrainingQueue -ErrorAction SilentlyContinue) {
        $q = CURRIC-GetTrainingQueue
        $curricPending = (@($q.items) | Where-Object { $_.status -eq "pending" }).Count
    }
    $curricView = @{
        pending_items = $curricPending
    }

    # Phase 82: Autonomy State
    $autoPending = 0
    $autoTopReason = $null
    if (Get-Command GATE-GetPendingRequests -ErrorAction SilentlyContinue) {
        $reqs = GATE-GetPendingRequests
        $autoPending = $reqs.Count
        if ($reqs.Count -gt 0) { $autoTopReason = $reqs[0].reasons -join "," }
    }
    $autonomyView = @{
        pending_requests = $autoPending
        top_reason       = $autoTopReason
    }


    # 3. Compose dashboard document
    $doc = [pscustomobject]@{
        version          = 1
        dashboard_id     = "AXIS-DASH-001"
        last_updated_utc = $now
        heartbeat        = $heartbeatView
        environment      = $envView
        router           = $routerView
        retina           = $retinaView
        shadow           = $shadowView
        neural_quarantine= $nqView
        symbiosis        = $symPreview
        bias             = $biasView
        anchor           = $anchorView
        curriculum       = $curricView
        autonomy         = $autonomyView
    }

    # 4. Persist
    $doc | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:DashboardStatePath -Encoding UTF8

    return $doc
}

function DASH-EmitHapticSignals {
    <#
    .SYNOPSIS
        Derive high-level haptic alerts from Dashboard_State + Shadow risk.
        Non-destructive: only appends alerts; does not change configs.
    #>
    param(
        [double] $NetworkRiskThreshold = 0.8,
        [double] $GlobalRiskThreshold  = 0.7
    )

    $dash = Load-JsonSafe -Path $Script:DashboardStatePath -Fallback $null
    if (-not $dash) { return }

    $shadow = $dash.shadow
    if (-not $shadow) { return }

    $bus = Load-JsonSafe -Path $Script:HapticAlertBusPath -Fallback @{
        version          = 1
        bus_id           = "AXIS-HAPTIC-001"
        last_updated_utc = $null
        alerts           = @()
    }

    if (-not $bus.alerts) { $bus.alerts = @() }

    $now = (Get-Date).ToUniversalTime().ToString("o")
    $newAlerts = @()

    # Example: network band high
    $netRisk = $shadow.bands.network
    if ($netRisk -ge $NetworkRiskThreshold) {
        $id = "HAPTIC-{0:yyyyMMddHHmmssfff}-NET" -f (Get-Date)
        $alert = [pscustomobject]@{
            alert_id       = $id
            timestamp_utc  = $now
            source         = "shadow"
            severity       = "high"
            channel        = "network"
            pattern        = "triple_pulse"
            duration_ms    = 900
            repeat         = 2
            message        = "Network risk $netRisk"
            consumed       = $false
        }
        $newAlerts += $alert
    }

    # Example: global spike
    $gRisk = $shadow.global_risk_score
    if ($gRisk -ge $GlobalRiskThreshold) {
        $id = "HAPTIC-{0:yyyyMMddHHmmssfff}-GLOBAL" -f (Get-Date)
        $alert = [pscustomobject]@{
            alert_id       = $id
            timestamp_utc  = $now
            source         = "shadow"
            severity       = "high"
            channel        = "global"
            pattern        = "long_pulse"
            duration_ms    = 1500
            repeat         = 1
            message        = "Global risk $gRisk"
            consumed       = $false
        }
        $newAlerts += $alert
    }

    if ($newAlerts.Count -eq 0) { return }

    $bus.alerts += $newAlerts
    # optional pruning
    if ($bus.alerts.Count -gt 500) {
        $bus.alerts = $bus.alerts | Sort-Object timestamp_utc | Select-Object -Last 500
    }

    $bus.last_updated_utc = $now
    $bus | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:HapticAlertBusPath -Encoding UTF8
}

function DASH-BuildUIInboxDashboard {
    <#
    .SYNOPSIS
        Generates top-level inbox cards for the UI.
    #>
    param()
    
    $dashboard = DASH-BuildDashboardState
    if (-not $dashboard) { return }
    
    $cards = @()
    
    # Heartbeat
    $hb = $dashboard.heartbeat
    $hbStatus = if ($hb.status) { $hb.status.ToUpper() } else { "UNKNOWN" }
    $cards += @{
        card_id = "UI-DASH-HEARTBEAT"
        type = "status"
        title = "Heartbeat"
        subtitle = "$hbStatus " + [char]0x2022 + " $($hb.bpm) BPM"
        severity = if ($hbStatus -eq "OK" -or $hbStatus -eq "GREEN") { "low" } else { "medium" }
        status = $hb.status
        source = "DASH-BuildUIInboxDashboard"
        actions = @(@{ action_id="view_symbiosis"; label="View Journal"; kind="primary" })
    }
    
    # Network
    $net = $dashboard.router
    $netAlerts = if ($net.alerts) { $net.alerts.Count } else { 0 }
    $cards += @{
        card_id = "UI-DASH-NETWORK"
        type = "status"
        title = "Network ($($net.hostname))"
        subtitle = "$($net.active_clients) clients " + [char]0x2022 + " Alerts: $netAlerts"
        severity = if ($netAlerts -gt 0) { "medium" } else { "low" }
        status = $net.status
        source = "DASH-BuildUIInboxDashboard"
        actions = @(@{ action_id="open_neural_review"; label="Review Neural"; kind="primary" })
    }
    
    # Shadow
    $shadow = $dashboard.shadow
    $risk = $shadow.global_risk_score
    
    $shadowText = "Global: $risk"
    if ($shadow.bands) {
        $shadowText += " " + [char]0x2022 + " Bands: "
        try {
            $props = $shadow.bands.PSObject.Properties | ForEach-Object { "$($_.Name)=$($_.Value)" }
            $shadowText += ($props -join ' ')
        } catch {
            $props = $shadow.bands.Keys | ForEach-Object { "$_=$($shadow.bands[$_])" }
            $shadowText += ($props -join ' ')
        }
    }
    
    $cards += @{
        card_id = "UI-DASH-SHADOW"
        type = "status"
        title = "Shadow Risk"
        subtitle = $shadowText
        severity = if ($risk -gt 0.5) { "high" } else { "low" }
        status = if ($risk -gt 0.5) { "warning" } else { "ok" }
        source = "DASH-BuildUIInboxDashboard"
        actions = @(@{ action_id="open_shadow_index"; label="Details"; kind="primary" })
    }
    
    $inbox = @{
        version = 1
        inbox_id = "UI-INBOX-DASHBOARD"
        generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        cards = $cards
    }
    
    $inbox | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:UIInboxDashboardPath -Encoding UTF8
}

# Export (Optional, commented out)
# Export-ModuleMember -Function DASH-BuildDashboardState, DASH-EmitHapticSignals, DASH-BuildUIInboxDashboard
