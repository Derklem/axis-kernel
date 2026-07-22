
# Haptic_Driver.ps1
# Phase 73: Bridge Haptic_Alert_Bus -> Physical Outputs

if (-not $Script:InfinityRoot) { $Script:InfinityRoot = "D:\Infinite" }

$Script:HapticBusPath        = Join-Path $Script:InfinityRoot "Infinity\UI\Haptic_Alert_Bus.json"
$Script:HapticRegistryPath   = Join-Path $Script:InfinityRoot "Infinity\UI\Haptic_Device_Registry.json"

# ----------------------------
# Helpers
# ----------------------------

function Get-HapticRegistry {
    if (-not (Test-Path -LiteralPath $Script:HapticRegistryPath)) {
        return @{ version = 1; devices = @() }
    }
    try {
        return Get-Content $Script:HapticRegistryPath -Raw | ConvertFrom-Json
    } catch {
        return @{ version = 1; devices = @() }
    }
}

function Get-HapticBus {
    if (-not (Test-Path -LiteralPath $Script:HapticBusPath)) {
        return @{ version = 1; alerts = @() }
    }
    try {
        return Get-Content $Script:HapticBusPath -Raw | ConvertFrom-Json
    } catch {
        return @{ version = 1; alerts = @() }
    }
}

function Save-HapticBus($doc) {
    try {
        # Ensure we write valid JSON and handle handle lock somewhat by basic retries implicitly via FS
        $doc | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $Script:HapticBusPath -Encoding UTF8
    } catch {
        if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
             Mind-Log "HAPTIC_ERR" "Failed to save Haptic Bus: $_"
        }
    }
}

# ----------------------------
# Pattern dispatch per device
# ----------------------------

function Invoke-HapticForDevice {
    param(
        [Parameter(Mandatory=$true)] $Device,
        [Parameter(Mandatory=$true)] [string] $Pattern,
        [Parameter(Mandatory=$true)] $Alert
    )

    if (-not $Device.enabled) { return }

    $type = $Device.type

    switch ($type) {
        "system_beep" {
            Invoke-HapticSystemBeep -Device $Device -Pattern $Pattern
        }
        "serial" {
            Invoke-HapticSerialDevice -Device $Device -Pattern $Pattern
        }
        default {
            # Unknown device type – ignore safely
        }
    }
}

function Invoke-HapticSystemBeep {
    param(
        [Parameter(Mandatory=$true)] $Device,
        [Parameter(Mandatory=$true)] [string] $Pattern
    )

    $endpoint = $Device.endpoint
    try {
        $minF = [int]($endpoint.min_freq_hz  | ForEach-Object { $_ }) # avoid nulls
        $maxF = [int]($endpoint.max_freq_hz  | ForEach-Object { $_ })
        if ($minF -le 0) { $minF = 400 }
        if ($maxF -le $minF) { $maxF = 2000 }

        $baseDur = [int]($endpoint.default_duration_ms | ForEach-Object { $_ })
        if ($baseDur -le 0) { $baseDur = 200 }

        switch ($Pattern) {
            "info" {
                [console]::Beep($minF, $baseDur)
            }
            "warn" {
                [console]::Beep([int](($minF + $maxF)/2), $baseDur)
                Start-Sleep -Milliseconds 100
                [console]::Beep([int](($minF + $maxF)/2), $baseDur)
            }
            "alert" {
                for ($i=0; $i -lt 3; $i++) {
                    [console]::Beep($maxF, $baseDur)
                    Start-Sleep -Milliseconds 75
                }
            }
            default {
                [console]::Beep($minF, $baseDur)
            }
        }
    } catch {
        # Beep might fail on some systems/hosts without speaker
    }
}

function Invoke-HapticSerialDevice {
    param(
        [Parameter(Mandatory=$true)] $Device,
        [Parameter(Mandatory=$true)] [string] $Pattern
    )

    $ep = $Device.endpoint
    $port = $ep.port
    $baud = $ep.baud
    $cmds = $ep.pattern_commands

    if (-not $port -or -not $baud -or -not $cmds) { return }
    if (-not $cmds.$Pattern) { return }

    $cmd = $cmds.$Pattern

    try {
        $portObj = New-Object System.IO.Ports.SerialPort $port, $baud, 'None', 8, 'One'
        $portObj.Open()
        $portObj.Write($cmd)
        $portObj.Close()
    } catch {
        # Fail silently into logs if Mind-Log available
        if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
            Mind-Log "HAPTIC_SERIAL" "Failed to send pattern '$Pattern' to ${port}: $_"
        }
    }
}

# ----------------------------
# Public Tools
# ----------------------------

function HAPTIC-DispatchBus {
    <#
    .SYNOPSIS
        Flushes Haptic_Alert_Bus.json and emits physical haptic signals.
    .DESCRIPTION
        Reads pending alerts, maps severities to patterns per device, sends signals,
        then marks alerts as dispatched.
    #>
    param(
        [int] $MaxAlerts = 20
    )

    $reg = Get-HapticRegistry
    $bus = Get-HapticBus

    if (-not $bus.alerts -or $bus.alerts.Count -eq 0) { return }

    $alerts = @($bus.alerts | Where-Object { -not $_.dispatched } | Sort-Object timestamp_utc)
    if ($MaxAlerts -gt 0) {
        $alerts = $alerts | Select-Object -First $MaxAlerts
    }

    if (-not $alerts -or $alerts.Count -eq 0) { return }

    $devices = @($reg.devices | Where-Object { $_.enabled -eq $true })
    if (-not $devices -or $devices.Count -eq 0) { return }
    
    $dispatchedCount = 0

    foreach ($alert in $alerts) {
        $sev = if ($alert.severity) { [string]$alert.severity } else { "low" }

        foreach ($dev in $devices) {
            $map = $dev.severity_map
            $pattern = if ($map -and $map.$sev) { $map.$sev } else { "info" }

            if ($dev.supported_patterns -and -not ($dev.supported_patterns -contains $pattern)) {
                continue
            }

            Invoke-HapticForDevice -Device $dev -Pattern $pattern -Alert $alert
        }
        
        # Need to update the bus object in memory
        $alert.dispatched = $true
        $alert.dispatched_at_utc = (Get-Date).ToUniversalTime().ToString("o")
        $dispatchedCount++
    }
    
    # Save back the whole bus (including dispatched edits)
    # Re-reading is safer but here we have the ref. 
    # $bus is the object. $bus.alerts was referenced.
    
    Save-HapticBus -doc $bus

    if (Get-Command Mind-Log -ErrorAction SilentlyContinue) {
        Mind-Log "HAPTIC_DISPATCH" "Dispatched $dispatchedCount alerts to $($devices.Count) devices."
    }
}

function HAPTIC-TestSignal {
    <#
    .SYNOPSIS
        Manually trigger a haptic signal for testing.
    #>
    param(
        [ValidateSet("low","medium","high","critical")]
        [string] $Severity = "low",
        [string] $Message = "Test haptic alert."
    )

    $reg = Get-HapticRegistry
    $devices = @($reg.devices | Where-Object { $_.enabled -eq $true })
    if (-not $devices -or $devices.Count -eq 0) {
        Write-Host "[HAPTIC] No enabled devices."
        return
    }

    foreach ($dev in $devices) {
        $map = $dev.severity_map
        $pattern = if ($map -and $map.$Severity) { $map.$Severity } else { "info" }

        if ($dev.supported_patterns -and -not ($dev.supported_patterns -contains $pattern)) {
            continue
        }

        Write-Host "[HAPTIC] Device $($dev.device_id) <- $Severity ($pattern): $Message"
        try {
            Invoke-HapticForDevice -Device $dev -Pattern $pattern -Alert @{ message=$Message; severity=$Severity }
        } catch {
             Write-Host "[HAPTIC] Output Error: $_"
        }
    }
}

# Export not needed for dot-sourcing but good for modules
# Export-ModuleMember -Function HAPTIC-DispatchBus, HAPTIC-TestSignal
