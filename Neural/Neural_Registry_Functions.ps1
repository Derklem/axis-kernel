
# ============================================================
# Neural Channel Registry Logic (Phase 64)
# ============================================================

# Global/path config (reuse InfinityRoot if already set)
if (-not $Script:InfinityRoot) { $Script:InfinityRoot = "D:\Infinite" }

$Script:NeuralRegistryPath  = Join-Path $Script:InfinityRoot "Infinity\Neural\Neural_Channel_Registry.json"
$Script:NeuralRegistryCache = $null

function Get-NeuralChannelRegistry {
    if ($Script:NeuralRegistryCache -ne $null) { return $Script:NeuralRegistryCache }

    if (-not (Test-Path -LiteralPath $Script:NeuralRegistryPath)) {
        $empty = [pscustomobject]@{ version=1; registry_id="NEURAL-REG-EMPTY"; channels=@() }
        $Script:NeuralRegistryCache = $empty
        return $empty
    }

    try {
        $json = Get-Content -LiteralPath $Script:NeuralRegistryPath -Raw -Encoding UTF8
        $reg  = $json | ConvertFrom-Json -ErrorAction Stop
        if (-not $reg.channels) { $reg | Add-Member -NotePropertyName channels -NotePropertyValue @() -Force }
        $Script:NeuralRegistryCache = $reg
        return $reg
    }
    catch {
        $msg = "Failed to parse Neural_Channel_Registry.json: $($_.Exception.Message)"
        if (Get-Command Mind-Log -ErrorAction SilentlyContinue) { Mind-Log "NEURAL_REG" $msg }
        return [pscustomobject]@{ version=1; registry_id="NEURAL-REG-ERROR"; channels=@() }
    }
}

function Save-NeuralChannelRegistry {
    param([Parameter(Mandatory=$true)]$Registry)
    $Registry | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:NeuralRegistryPath -Encoding UTF8
    $Script:NeuralRegistryCache = $Registry
    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "NEURAL_REG" "Saved Registry ($($Registry.channels.Count) channels)."
    }
}

function Get-NeuralChannels {
    param([string[]]$Status, [string[]]$Category, [string[]]$Tags)
    $reg = Get-NeuralChannelRegistry
    $channels = $reg.channels

    if ($Status) { $channels = $channels | Where-Object { $Status -contains $_.status } }
    if ($Category) { $channels = $channels | Where-Object { $Category -contains $_.category } }
    if ($Tags) {
        $channels = $channels | Where-Object {
            if (-not $_.tags) { return $false }
            foreach ($t in $Tags) { if ($_.tags -contains $t) { return $true } }
            return $false
        }
    }
    return $channels
}

function Get-NeuralChannelById {
    param([Parameter(Mandatory=$true)][string]$ChannelId)
    $reg = Get-NeuralChannelRegistry
    return ($reg.channels | Where-Object { $_.channel_id -eq $ChannelId })
}

function Set-NeuralChannelStatus {
    param(
        [Parameter(Mandatory=$true)][string]$ChannelId,
        [Parameter(Mandatory=$true)][ValidateSet("enabled","disabled","quarantined","experimental")][string]$Status
    )
    $reg = Get-NeuralChannelRegistry
    $found = $false
    foreach ($ch in $reg.channels) {
        if ($ch.channel_id -eq $ChannelId) {
            $ch.status = $Status
            $ch.updated_at = (Get-Date).ToUniversalTime().ToString("o")
            $found = $true; break
        }
    }
    if ($found) { Save-NeuralChannelRegistry -Registry $reg }
}

function Update-NeuralChannelHealth {
    param(
        [Parameter(Mandatory=$true)][string]$ChannelId,
        [string]$LastStatus, [string]$LastError, [string]$LastSeenUtc
    )
    $reg = Get-NeuralChannelRegistry
    $found = $false
    $now = (Get-Date).ToUniversalTime().ToString("o")

    foreach ($ch in $reg.channels) {
        if ($ch.channel_id -eq $ChannelId) {
            if (-not $ch.health) { $ch | Add-Member -NotePropertyName health -NotePropertyValue @{} -Force }
            $ch.health.last_seen_utc = if ($LastSeenUtc) { $LastSeenUtc } else { $now }
            if ($LastStatus) { $ch.health.last_status = $LastStatus }
            if ($LastError -ne $null) { $ch.health.last_error = $LastError }
            $ch.updated_at = $now
            $found = $true; break
        }
    }
    if ($found) { Save-NeuralChannelRegistry -Registry $reg }
}

function Update-NeuralChannelMetrics {
    param(
        [Parameter(Mandatory=$true)][string]$ChannelId,
        [double]$AvgEventsPerMin, [double]$ErrorRate
    )
    $reg = Get-NeuralChannelRegistry
    $found = $false
    $now = (Get-Date).ToUniversalTime().ToString("o")

    foreach ($ch in $reg.channels) {
        if ($ch.channel_id -eq $ChannelId) {
            if (-not $ch.metrics) { $ch | Add-Member -NotePropertyName metrics -NotePropertyValue @{} -Force }
            if ($PSBoundParameters.ContainsKey('AvgEventsPerMin')) { $ch.metrics.avg_events_per_min = $AvgEventsPerMin }
            if ($PSBoundParameters.ContainsKey('ErrorRate')) { $ch.metrics.error_rate = $ErrorRate }
            $ch.updated_at = $now
            $found = $true; break
        }
    }
    if ($found) { Save-NeuralChannelRegistry -Registry $reg }
}

function Set-NeuralChannelRateLimit {
    param(
        [Parameter(Mandatory=$true)][string]$ChannelId,
        [int]$MaxEventsPerMin, [int]$BurstLimit
    )
    $reg = Get-NeuralChannelRegistry
    $found = $false
    $now = (Get-Date).ToUniversalTime().ToString("o")

    foreach ($ch in $reg.channels) {
        if ($ch.channel_id -eq $ChannelId) {
            if (-not $ch.rate_limit) { $ch | Add-Member -NotePropertyName rate_limit -NotePropertyValue @{} -Force }
            if ($PSBoundParameters.ContainsKey('MaxEventsPerMin')) { $ch.rate_limit.max_events_per_min = $MaxEventsPerMin }
            if ($PSBoundParameters.ContainsKey('BurstLimit')) { $ch.rate_limit.burst_limit = $BurstLimit }
            $ch.updated_at = $now
            $found = $true; break
        }
    }
    if ($found) { Save-NeuralChannelRegistry -Registry $reg }
}
