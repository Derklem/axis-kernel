# -------------------------------
# Axis Audit Dashboard (T26)
# -------------------------------
# Description: Provides a high-fidelity, non-interactive view of the system state.
# Status: Phase 632 (Operational Hardening)

$RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$ModeFile = Join-Path $RuntimeDir "system_mode.json"
$ConstraintsPath = "D:\Infinite\Infinity\Governance\Constitutional_Constraints.json"
$MetricsPath = "D:\Infinite\Infinity\Runtime\Decision\metrics_snapshot.json"
$ResonancePath = "D:\Infinite\Infinity\Runtime\Decision\Resonance_State.json"

function Show-Dashboard {
    Clear-Host
    Write-Host "=== AXIS AUDIT DASHBOARD [STABLE] ===" -ForegroundColor Gray
    Write-Host "TS: $((Get-Date).ToUniversalTime().ToString('o'))" -ForegroundColor DarkGray
    Write-Host "-------------------------------------"

    # 1. System Mode
    if (Test-Path $ModeFile) {
        $mode = Get-Content $ModeFile | ConvertFrom-Json
        $color = if ($mode.mode -eq "OBSERVATION_ONLY") { "Cyan" } else { "Red" }
        Write-Host "MODE:     $($mode.mode)" -ForegroundColor $color
        Write-Host "WRITES:   $($mode.writes_enabled)" -ForegroundColor $color
    }

    # 2. Resonance
    if (Test-Path $ResonancePath) {
        $res = Get-Content $ResonancePath | ConvertFrom-Json
        $capStatus = if ($res.cap_enforced) { " [CAP ENFORCED]" } else { "" }
        Write-Host "RESONANCE: $($res.score) [$($res.status)]$capStatus" -ForegroundColor Yellow
        Write-Host "  RAW:     $($res.raw_score)" -ForegroundColor DarkYellow
        Write-Host "  CAP:     $($res.cap)" -ForegroundColor DarkGray
    }

    # 3. Constraints
    if (Test-Path $ConstraintsPath) {
        $constraints = Get-Content $ConstraintsPath | ConvertFrom-Json
        Write-Host "CONSTRAINTS: $($constraints.active_constraints.Count) Active" -ForegroundColor Green
        foreach ($c in $constraints.active_constraints) {
            Write-Host "  - [$($c.id)] $($c.description)" -ForegroundColor DarkGreen
        }
    }

    # 4. Metrics
    if (Test-Path $MetricsPath) {
        $metrics = Get-Content $MetricsPath | ConvertFrom-Json
        Write-Host "METRICS:  EMA_DRIFT: $($metrics.ema_drift)" -ForegroundColor White
    }

    Write-Host "-------------------------------------"
    Write-Host "[SYSTEM OMNI / GROUNDED]" -ForegroundColor DarkGray
}

# Continuous loop for dashboard
while ($true) {
    Show-Dashboard
    Start-Sleep -Seconds 5
}
