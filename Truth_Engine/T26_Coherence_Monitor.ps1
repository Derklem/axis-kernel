<#
.SYNOPSIS
  T26_Coherence_Monitor.ps1
  Calculates the 'Resonance' between the User's architectural blueprints and system state.
#>

$MindPulsePath = "D:\Infinite\Infinity\Mind_Pulse.json"
$NeuralLedgerPath = "D:\Infinite\Infinity\Memory\indexes\Neural_Pulse_Ledger.jsonl"
$ResonancePath = "D:\Infinite\Infinity\Memory\indexes\Resonance_State.json"

function Get-Resonance {
    if (-not (Test-Path $NeuralLedgerPath)) { return 0.0 }
    
    $raw = Get-Content $NeuralLedgerPath
    if ($null -eq $raw -or $raw.Count -eq 0) { return 0.0 }
    
    $latestShard = $raw[-1] | ConvertFrom-Json
    if (-not $latestShard) { return 0.0 }

    # Precise Date Handling
    $shardTs = [DateTime]::Parse($latestShard.ts_utc, $null, [System.Globalization.DateTimeStyles]::AdjustToUniversal)
    $now = [DateTime]::UtcNow
    $diff = ($now - $shardTs).TotalMinutes

    # Heuristic: 1.0 resonance if anchored in the last 15 mins, decaying to 0.5 over 24h.
    $resonance = 1.0
    if ($diff -gt 15) {
        $resonance = [Math]::Max(0.5, 1.0 - ($diff / 1440))
    }
    elseif ($diff -lt 0) {
        # Future-dated (clock skew)? 1.0 resonance.
        $resonance = 1.0
    }

    # 4. Pattern Weight (Shard > Pulse > Draft)
    $weight = 1.0
    if ($latestShard.kind -eq "neural_pulse") { $weight = 0.9 }
    if ($latestShard.kind -eq "neural_draft") { $weight = 0.7 }

    $final = [Math]::Round(($resonance * $weight), 2)
    return $final
}

$score = Get-Resonance
$status = if ($score -ge 0.9) { "COHERENT" } else { "STABLE" }

$lastShardObj = (Get-Content $NeuralLedgerPath)[-1] | ConvertFrom-Json

$resState = [ordered]@{
    ts_utc    = [DateTime]::UtcNow.ToString("o")
    resonance = $score
    mode      = $status
    anchor_pk = $lastShardObj.pk
}

$resState | ConvertTo-Json | Set-Content $ResonancePath

Write-Host "[INTEGRAL] System Resonance: $score ($status)" -ForegroundColor Cyan
