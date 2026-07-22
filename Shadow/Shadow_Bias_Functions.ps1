
# Shadow_Bias_Functions.ps1
# Phase 72: Shadow-Aware Strategy Bias
# Helper functions to calculate bias state and annotation strategies.

if (-not $Script:InfinityRoot) { $Script:InfinityRoot = "D:\Infinite" }
$Script:ShadowRiskIndexPath = Join-Path $Script:InfinityRoot "Infinity\Shadow\Shadow_Risk_Index.json"
$Script:ShadowBiasProfilePath = Join-Path $Script:InfinityRoot "Infinity\Shadow\Shadow_Bias_Profile.json"

function Get-ShadowBiasProfile {
    $fallback = @{
        version      = 1
        profile_id   = "SHADOW-BIAS-DEFAULT"
        global_modes = @{
            normal   = @{ global_threshold = 0.3 }
            watch    = @{ global_threshold = 0.6 }
            elevated = @{ global_threshold = 0.8 }
            critical = @{ global_threshold = 0.95 }
        }
        band_bias    = @{}
    }

    if (-not (Test-Path -LiteralPath $Script:ShadowBiasProfilePath)) { return $fallback }
    try {
        return Get-Content $Script:ShadowBiasProfilePath -Raw | ConvertFrom-Json
    }
    catch {
        return $fallback
    }
}

function Get-ShadowBiasState {
    $risk = @{
        summary          = @{
            global_risk_score = 0.0
            bands             = @{
                system      = 0.0
                network     = 0.0
                environment = 0.0
                visual      = 0.0
            }
        }
        last_updated_utc = $null
    }

    if (Test-Path -LiteralPath $Script:ShadowRiskIndexPath) {
        try {
            $risk = Get-Content $Script:ShadowRiskIndexPath -Raw | ConvertFrom-Json
        }
        catch {}
    }

    $prof = Get-ShadowBiasProfile
    $g = [double]$risk.summary.global_risk_score

    # global mode resolution – handle PSCustomObject or Hashtable
    $modes = if ($prof.global_modes.PSObject) {
        $prof.global_modes.PSObject.Properties | Where-Object { $_.MemberType -eq "NoteProperty" } | Select-Object @{N = "Key"; E = { $_.Name } }, @{N = "Value"; E = { $_.Value } }
    }
    else {
        $prof.global_modes.GetEnumerator()
    }
    
    $sortedModes = $modes | Sort-Object { [double]$_.Value.global_threshold }
    $globalMode = "normal"
    
    foreach ($m in $sortedModes) {
        if ($g -ge [double]$m.Value.global_threshold) {
            $globalMode = $m.Key
        }
    }

    $bands = $risk.summary.bands
    $bandModes = @{
        system      = "normal"
        network     = "normal"
        environment = "normal"
        visual      = "normal"
    }
    
    if ($bands) {
        # Handle PSCustomObject vs Hashtable
        try {
            $keys = $bands.PSObject.Properties.Name
        }
        catch {
            $keys = $bands.Keys
        }
        
        foreach ($b in $keys) {
            $v = [double]$bands.$b
            if ($v -ge 0.7) { $bandModes[$b] = "elevated" }
            elseif ($v -ge 0.4) { $bandModes[$b] = "watch" }
        }
    }

    return @{
        global_mode  = $globalMode
        global_score = $g
        band_modes   = $bandModes
        bands        = $bands
        last_updated = $risk.last_updated_utc
        profile_id   = $prof.profile_id
    }
}

function Get-StrategyBiasAnnotation {
    param(
        [Parameter(Mandatory = $true)] $StrategyDef,
        [Parameter(Mandatory = $true)] $BiasState
    )

    $cat = $StrategyDef.category
    $id = $StrategyDef.id
    $autonomy = $StrategyDef.autonomy_level

    $globalMode = $BiasState.global_mode
    $bandModes = $BiasState.band_modes

    # compute basic label and priority (low number = earlier)
    $priority = 10
    $labels = @()
    
    # Global mode influence
    switch ($globalMode) {
        "normal" { $priority = 10 }
        "watch" { $priority = 8; $labels += "global_watch" }
        "elevated" { $priority = 6; $labels += "global_elevated" }
        "critical" { $priority = 4; $labels += "global_critical" }
    }

    # Per-band: check relevant band for this strategy
    $band = "system"
    if ($cat -match "network|router|net") { $band = "network" }
    elseif ($cat -match "environment|weather") { $band = "environment" }
    elseif ($cat -match "visual|retina|neural") { $band = "visual" }

    $bandMode = "normal"
    if ($bandModes.ContainsKey($band)) {
        $bandMode = $bandModes[$band]
    }

    if ($bandMode -eq "elevated") {
        $priority -= 2
        $labels += "band_${band}_elevated"
    }
    elseif ($bandMode -eq "watch") {
        $priority -= 1
        $labels += "band_${band}_watch"
    }

    # Ensure bounds
    if ($priority -lt 1) { $priority = 1 }

    # Flags for UI: is this strategy "promoted" or "background"?
    $promoted = $priority -le 6
    $background = ($globalMode -eq "critical" -and -not $promoted)

    return @{
        bias_priority   = $priority
        bias_labels     = $labels
        band            = $band
        promoted        = $promoted
        background_hint = $background
    }
}
