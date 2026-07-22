<#
.SYNOPSIS
  T33_AutonomyBudget.ps1
  Node 3 Budget & Circuit Breaker Manager.
  Checks Receipt Ledger for backpressure signals (429/503).
.OUTPUTS
  JSON { allowed: bool, reason: string, mode_override: string }
#>

param()

$ConfigPath = "D:\Infinite\Infinity\Runtime\Autonomy\autonomy_config.json"
$LedgerPath = "D:\Infinite\Infinity\Runtime\Receipts\Receipt_Ledger.jsonl"

# Default result (Fail open or closed? Closed for safety)
$result = [ordered]@{
    allowed       = $false
    reason        = "init"
    mode_override = $null
}

if (-not (Test-Path $ConfigPath)) {
    $result.reason = "config_missing"
    $result | ConvertTo-Json -Compress
    return
}

try {
    $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
    $windowMins = $config.constraints.circuit_breaker_window_minutes
    $codes = $config.constraints.circuit_breaker_error_codes
    
    # 1. Check Circuit Breaker (Ledger Scan)
    if (Test-Path $LedgerPath) {
        $since = (Get-Date).AddMinutes(-$windowMins).ToUniversalTime()
        # Increased tail to 200 to capture fuller history, parsed line-by-line
        $lines = Get-Content $LedgerPath -Tail 200 
        
        foreach ($line in $lines) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }

            $entry = $null
            try { $entry = $line | ConvertFrom-Json } catch { continue }
            if (-not $entry -or -not $entry.ts) { continue }

            $ts = $null
            try { $ts = [DateTimeOffset]::Parse([string]$entry.ts).ToUniversalTime() } catch { continue }
            if ($ts -lt $since) { continue }

            # Guard: only process receipts
            if ($entry.type -ne "RECEIPT" -or -not $entry.receipt) { continue }

            $http = $null
            try { $http = [int]$entry.receipt.http_status } catch { $http = $null }

            $status = $null
            if ($entry.receipt.PSObject.Properties.Name -contains "status") { $status = [string]$entry.receipt.status }

            $reason = $null
            if ($entry.receipt.PSObject.Properties.Name -contains "reason") { $reason = [string]$entry.receipt.reason }

            # Trip conditions
            $trip = $false
            if ($http -ne $null -and ($http -in $codes)) { $trip = $true }
            if (-not $trip -and $status -eq "rejected" -and $reason -match "429") { $trip = $true }

            if ($trip) {
                $result.allowed = $false # Strict semantic: execution disallowed
                $result.reason = "circuit_breaker_active"
                $result.mode_override = "PROPOSE_ONLY" # Hint: Downgrade is possible
                
                # Return immediately
                $result | ConvertTo-Json -Compress
                return
            }
        }
    }
    
    # 2. If no breaker, we are allowed based on config
    $result.allowed = $true
    $result.reason = "nominal"
    $result.mode_override = $null # Usage of config.autonomy_mode logic is downstream
}
catch {
    $result.allowed = $false
    $result.reason = "exception_during_check_$_"
}

$result | ConvertTo-Json -Compress
