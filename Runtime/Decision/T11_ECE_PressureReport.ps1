<#
.SYNOPSIS
  T11_ECE_PressureReport.ps1
.DESCRIPTION
  Computes rolling pressure stats from ece_events.jsonl for DDE gating.
#>
param(
    [int]$Minutes = 10,
    [string]$EpistemicDir = "D:\Infinite\Infinity\Runtime\Epistemic",
    [string]$OutPath = "D:\Infinite\Infinity\Runtime\Epistemic\ece_pressure.json"
)

$eventsFile = Join-Path $EpistemicDir "ece_events.jsonl"
if (-not(Test-Path $eventsFile)) { Write-Host "No ece_events.jsonl"; return }

$cut = (Get-Date).ToUniversalTime().AddMinutes(-1 * $Minutes)
$lines = Get-Content $eventsFile -Tail 2000

$events = @()
foreach ($line in $lines) {
    try { $e = $line | ConvertFrom-Json } catch { continue }
    if ($e.event_type -ne "ece_scored") { continue }
    try { $ts = [DateTime]$e.ts } catch { continue }
    if ($ts -lt $cut) { continue }
    $events += $e
}

if ($events.Count -eq 0) {
    $out = [ordered]@{ 
        ts          = (Get-Date).ToUniversalTime().ToString("o")
        window_min  = $Minutes
        count       = 0
        avg_score   = 0
        accept_rate = 0
        verdicts    = [ordered]@{ accept = 0; downweight = 0; quarantine = 0 }
        by_channel  = @{}
    }
    $out | ConvertTo-Json -Depth 6 | Set-Content $OutPath -Encoding UTF8 -Force
    return
}

$avg = [Math]::Round((($events | Measure-Object -Property score -Average).Average), 2)
$accept = @($events | Where-Object { $_.verdict -eq "accept" }).Count
$down = @($events | Where-Object { $_.verdict -eq "downweight" }).Count
$q = @($events | Where-Object { $_.verdict -eq "quarantine" }).Count

# per-channel avg
$byChan = @{}
foreach ($g in ($events | Group-Object channel)) {
    $byChan[$g.Name] = [ordered]@{
        count     = $g.Count
        avg_score = [Math]::Round((($g.Group | Measure-Object -Property score -Average).Average), 2)
        accept    = [int](@($g.Group | Where-Object { $_.verdict -eq "accept" }).Count)
    }
}

$out = [ordered]@{
    ts          = (Get-Date).ToUniversalTime().ToString("o")
    window_min  = $Minutes
    count       = $events.Count
    avg_score   = $avg
    accept_rate = [Math]::Round(($accept / [double]$events.Count), 3)
    verdicts    = [ordered]@{ accept = $accept; downweight = $down; quarantine = $q }
    by_channel  = $byChan
}

$out | ConvertTo-Json -Depth 8 | Set-Content $OutPath -Encoding UTF8 -Force
Write-Host "Wrote ECE Pressure Report to $OutPath"
