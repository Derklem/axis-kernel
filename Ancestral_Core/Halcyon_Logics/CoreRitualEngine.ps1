# === Core Ritual Engine ===
$basePath = "E:\Halcyon_Logics"
$ritualFile = "$basePath\rituals.cfg"
$logFile = "$basePath\halcyon_ritual_trace.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

if (-not (Test-Path $logFile)) {
    New-Item -ItemType File -Path $logFile | Out-Null
}

function Get-SigilCount {
    $sigilPath = "$basePath\sigil_log\sigil_tether_$(Get-Date -Format 'yyyyMMdd').log"
    return if (Test-Path $sigilPath) { (Get-Content $sigilPath | Measure-Object).Count } else { 0 }
}

function Get-TremorDelta {
    $tremorPath = "$basePath\echo_tremor.log"
    return if (Test-Path $tremorPath) { (Get-Content $tremorPath | Measure-Object).Count } else { 0 }
}

while ($true) {
    if (-not (Test-Path $ritualFile)) {
        Add-Content -Path $logFile -Value "[RITUAL_ENGINE] $timestamp :: No ritual file found."
        Start-Sleep -Seconds 600
        continue
    }

    $rituals = Get-Content $ritualFile -Raw -Encoding UTF8 -ErrorAction SilentlyContinue -Delimiter "`n`n"
    $sigilCount = Get-SigilCount
    $tremorCount = Get-TremorDelta

    foreach ($ritual in $rituals) {
        if ($ritual -match "Name\s*=\s*(.+)") { $name = $matches[1].Trim() }
        if ($ritual -match "Trigger\s*=\s*(.+)") { $trigger = $matches[1].Trim() }
        if ($ritual -match "Action\s*=\s*(.+)") { $action = $matches[1].Trim() }

        $condition = $trigger -replace "sigil_count", $sigilCount -replace "tremor_delta", $tremorCount

        try {
            if (Invoke-Expression $condition) {
                Add-Content -Path $logFile -Value "[RITUAL_TRIGGERED] $timestamp :: $name"
                Invoke-Expression $action
            }
        } catch {
            Add-Content -Path $logFile -Value "[RITUAL_ERROR] $timestamp :: Failed to evaluate $name"
        }
    }

    Start-Sleep -Seconds 600  # Every 10 minutes
}
