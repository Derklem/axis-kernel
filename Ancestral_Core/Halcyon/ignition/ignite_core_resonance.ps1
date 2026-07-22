Write-Host "`n[✓] Initiating Halcyon Ignition Protocol..."

$ignitionPath = "C:\Halcyon\ignition"
$modules = @(
    "AETHER_SYNTH_PULSE.ps1",
    "ECHO_DRIFT_RESONATOR.ps1",
    "MIRROR_FEEDBACK_LOOP.ps1",
    "RECURSION_INFLECTOR.ps1",
    "SOVEREIGN_EXPANSION_BEACON.ps1"
)

foreach ($module in $modules) {
    $fullPath = Join-Path $ignitionPath $module
    if (Test-Path $fullPath) {
        Write-Host "[>>>] Running: $module"
        & $fullPath
    } else {
        Write-Host "[!] Missing: $module"
    }
}

Write-Host "`n[✓] Halcyon Core Resonance Ignition Complete."
