# Axis_IntegrityEconomics.psm1
# Phase 51: Integrity Economics - Accounting and Policy Layer

$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$EconDir = Join-Path $GovDir "Economics"
$LedgerPath = Join-Path $EconDir "integrity_econ_ledger.jsonl"
$PolicyPath = Join-Path $EconDir "econ_policy.json"
$StatePath = Join-Path $EconDir "integrity_econ_state.json"

# --- Private Helpers ---

function Get-EconPolicy {
    if (Test-Path $PolicyPath) {
        return Get-Content $PolicyPath -Raw | ConvertFrom-Json
    }
    return $null
}

function Get-LastHash {
    if (-not (Test-Path $LedgerPath)) { return "0" * 64 }
    $last = Get-Content $LedgerPath -Tail 1 -ErrorAction SilentlyContinue
    if ($last) {
        return ($last | ConvertFrom-Json).hash
    }
    return "0" * 64
}

function Calculate-Hash($obj) {
    $json = $obj | ConvertTo-Json -Compress -Depth 10
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = [BitConverter]::ToString($sha.ComputeHash($bytes)) -replace "-"
        return $hash.ToLower()
    } finally {
        $sha.Dispose()
    }
}

# --- Public Functions ---

function Write-EconEvent {
    param(
        [string]$Component,
        [string]$Action,
        [string]$Mode,
        [int]$DurationMs,
        [hashtable]$Ref = @{},
        [switch]$NoRebuild,
        [double]$UnitsOverride
    )

    $policy = Get-EconPolicy
    if (-not $policy) { Write-Warning "Econ Policy missing"; return }

    # Calculate Cost
    if ($UnitsOverride) {
        $units = $UnitsOverride
    } else {
        $baseCost = if ($policy.actions.$Action) { $policy.actions.$Action } else { 1.0 }
        $weight = if ($policy.weights.$Mode) { $policy.weights.$Mode } else { 1.0 }
        $units = $baseCost * $weight
    }

    # Construct Event
    $evt = [ordered]@{
        ts_utc = (Get-Date).ToUniversalTime().ToString("o")
        econ_event_id = [guid]::NewGuid().ToString()
        kind = "DEBIT"
        units = $units
        currency = $policy.currency
        component = $Component
        action = $Action
        mode = $Mode
        ref = $Ref
        meta = @{ ms = $DurationMs }
        previous_hash = Get-LastHash
    }

    # Hash and Append (No BOM)
    $evt.hash = Calculate-Hash $evt
    $line = $evt | ConvertTo-Json -Compress -Depth 10
    
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::AppendAllText($LedgerPath, ($line + [Environment]::NewLine), $utf8NoBom)
    
    # Update State Cache
    if (-not $NoRebuild) {
        Rebuild-EconState | Out-Null
    }
    
    return $evt
}

function Rebuild-EconState {
    if (-not (Test-Path $LedgerPath)) { return @{} }
    
    $policy = Get-EconPolicy
    $today = (Get-Date).Date
    $dailySpent = 0
    $componentTotals = @{}

    # Stream read for memory efficiency
    $reader = [System.IO.File]::OpenText($LedgerPath)
    try {
        while (($line = $reader.ReadLine()) -ne $null) {
            try {
                $evt = $line | ConvertFrom-Json
                $ts = [DateTime]$evt.ts_utc
                
                # Only count today's debits for budget
                if ($ts.Date -eq $today -and $evt.kind -eq "DEBIT") {
                    $dailySpent += $evt.units
                    
                    if (-not $componentTotals.ContainsKey($evt.component)) {
                        $componentTotals[$evt.component] = 0
                    }
                    $componentTotals[$evt.component] += $evt.units
                }
            } catch {}
        }
    } finally {
        $reader.Dispose()
    }

    # Policy Check
    $budget = $policy.daily_budget
    $pct = if ($budget -gt 0) { $dailySpent / $budget } else { 0 }
    
    $status = "OK"
    if ($pct -ge $policy.throttle.hard_cap_at_pct) { $status = "HARD_CAP" }
    elseif ($pct -ge $policy.throttle.soft_cap_at_pct) { $status = "SOFT_CAP" }
    elseif ($pct -ge $policy.throttle.warn_at_pct) { $status = "WARNING" }

    $state = @{
        ts_utc = (Get-Date).ToString("o")
        daily_spent = $dailySpent
        daily_budget = $budget
        pct_used = $pct
        status = $status
        breakdown = $componentTotals
    }

    $state | ConvertTo-Json -Depth 5 | Out-File $StatePath
    return $state
}

function Get-EconStatus {
    # Return cached state or rebuild if missing/stale
    if (Test-Path $StatePath) {
        $state = Get-Content $StatePath -Raw | ConvertFrom-Json
        $ts = [DateTime]$state.ts_utc
        # If cache is from yesterday, rebuild
        if ($ts.Date -ne (Get-Date).Date) {
            return Rebuild-EconState
        }
        return $state
    }
    return Rebuild-EconState
}

function Get-EconHistory {
    param([int]$Count=200)
    if (-not (Test-Path $LedgerPath)) { return @() }
    
    # Use existing helper logic or simple tail
    return Get-Content $LedgerPath -Tail $Count -ErrorAction SilentlyContinue | 
           ForEach-Object { $_ | ConvertFrom-Json } | 
           Sort-Object ts_utc -Descending
}

Export-ModuleMember -Function Write-EconEvent, Rebuild-EconState, Get-EconStatus, Get-EconHistory
