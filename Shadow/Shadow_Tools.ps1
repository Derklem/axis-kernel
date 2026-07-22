
# ============================================================
# SHADOW-Ingest-NeuralEvents
# ============================================================

if (-not $Script:InfinityRoot) { $Script:InfinityRoot = "D:\Infinite" }
$Script:NeuralEventIndexPath = Join-Path $Script:InfinityRoot "Infinity\Neural\Neural_Event_Index.json"
$Script:ShadowRiskIndexPath = Join-Path $Script:InfinityRoot "Infinity\Shadow\Shadow_Risk_Index.json"

function SHADOW-Ingest-NeuralEvents {
    <#
    .SYNOPSIS
        Derive risk signals from Neural_Event_Index and update Shadow_Risk_Index.json.
    #>
    param(
        [int] $LookbackMinutes = 30,
        [int] $MaxSignals = 200
    )

    Write-Output "[SHADOW-INGEST] Starting Ingestion (Lookback=$LookbackMinutes)..."

    if (-not (Test-Path -LiteralPath $Script:NeuralEventIndexPath)) { 
        Write-Output "[SHADOW-INGEST] ERR: Neural index not found at $Script:NeuralEventIndexPath"
        return 
    }

    try {
        $idx = Get-Content -LiteralPath $Script:NeuralEventIndexPath -Raw | ConvertFrom-Json
        $events = if ($idx.events) { @($idx.events) } else { @() }
    }
    catch { 
        Write-Output "[SHADOW-INGEST] ERR: Failed to parse Neural Index: $_"
        return 
    }

    if ($events.Count -eq 0) { 
        Write-Output "[SHADOW-INGEST] No events in index."
        return 
    }

    $cutoff = (Get-Date).ToUniversalTime().AddMinutes(-$LookbackMinutes)
    Write-Output "[SHADOW-INGEST] Cutoff: $($cutoff.ToString('o'))"

    # Filter recent events
    $recent = $events | Where-Object {
        try {
            $ts = [DateTime]::Parse($_.timestamp_utc).ToUniversalTime()
            $ts -ge $cutoff
        }
        catch { $false }
    }
    
    if (-not $recent) { 
        Write-Output "[SHADOW-INGEST] No recent events within lookback."
        return 
    }

    Write-Output "[SHADOW-INGEST] Processing $($recent.Count) recent events..."

    # Load existing risk index
    $risk = @{
        version          = 1
        index_id         = "SHADOW-RISK-2026-001"
        last_updated_utc = $null
        summary          = @{
            global_risk_score = 0.0
            bands             = @{
                system      = 0.0
                network     = 0.0
                environment = 0.0
                visual      = 0.0
            }
        }
        signals          = @()
    }

    if (Test-Path -LiteralPath $Script:ShadowRiskIndexPath) {
        try { 
            $data = Get-Content -LiteralPath $Script:ShadowRiskIndexPath -Raw | ConvertFrom-Json
            if ($data) { $risk = $data }
        }
        catch { }
    }

    [System.Collections.ArrayList]$sigList = @()
    if ($risk.signals) { foreach ($s in $risk.signals) { $sigList.Add($s) | Out-Null } }

    foreach ($evt in $recent) {
        $ts = [DateTime]::Parse($evt.timestamp_utc).ToUniversalTime()
        $band = "system"
        $score = 0.0
        $tags = @()
        $etype = [string]$evt.type
        $chan = [string]$evt.channel_id

        switch -Wildcard ($etype) {
            "governance_flux" {
                $band = "system"
                $tags = @($evt.alerts) + "governance"
                $score = [Math]::Min(0.8, 0.1 * ($evt.event_count))
            }
            "treaty_dissonance" {
                $band = "network"
                $tags = @($evt.alerts) + "federation"
                $score = [Math]::Min(0.9, 0.5 + 0.1 * ($evt.unresolved_count))
            }
            "router_anomaly" {
                $band = "network"
                $tags = @($evt.alerts) + "router"
                $score = [Math]::Min(1.0, 0.2 + 0.1 * ($evt.alerts.Count))
            }
            "weather_alert" {
                $band = "environment"
                $tags = @($evt.alerts) + "weather"
                $score = 0.3
            }
            "retina_frame" {
                $band = "visual"
                $tags = @($evt.tags) + @($evt.alerts) + "retina"
                $score = if ($evt.highlight -eq $true) { 0.4 } else { 0.1 }
            }
            default {
                $band = "system"
                $tags = @($evt.type)
                $score = 0.1
            }
        }

        if ($score -le 0) { continue }

        $sigId = "SIG-{0:yyyyMMddHHmmssfff}-{1}" -f $ts, ($band.ToUpper())
        
        # Check if exists
        $exists = $sigList | Where-Object { $_.signal_id -eq $sigId }
        if ($exists) { continue }

        $signal = [pscustomobject]@{
            signal_id             = $sigId
            timestamp_utc         = $evt.timestamp_utc
            source_channel        = $chan
            source_event_type     = $etype
            band                  = $band
            risk_score            = [Math]::Round($score, 3)
            tags                  = $tags
            derived_from_event_ts = $evt.timestamp_utc
        }

        $sigList.Add($signal) | Out-Null
    }

    # Prune signals
    $finalSigs = $sigList.ToArray() | Sort-Object timestamp_utc | Select-Object -Last $MaxSignals
    
    # Recompute summary
    $bands = @{ system = 0.0; network = 0.0; environment = 0.0; visual = 0.0 }
    foreach ($s in $finalSigs) {
        $b = $s.band
        if ($bands.ContainsKey($b)) {
            if ($s.risk_score -gt $bands[$b]) { $bands[$b] = $s.risk_score }
        }
    }

    $riskData = [ordered]@{
        version          = 1
        index_id         = "SHADOW-RISK-2026-001"
        last_updated_utc = (Get-Date).ToUniversalTime().ToString("o")
        summary          = @{
            global_risk_score = [Math]::Round(($bands.Values | Measure-Object -Maximum).Maximum, 3)
            bands             = $bands
        }
        signals          = $finalSigs
    }

    $riskData | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Script:ShadowRiskIndexPath -Encoding UTF8
    Write-Output "[SHADOW-INGEST] Successfully updated Risk Index. Global Score: $($riskData.summary.global_risk_score)"
}
