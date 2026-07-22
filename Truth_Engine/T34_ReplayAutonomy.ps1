<#
.SYNOPSIS
  T34_ReplayAutonomy.ps1
  Node 3.1 Deterministic Replay Engine.
  Reads a ledger (Real or Test) and computes Effective Mode based on invariants.
  
.PARAMETER LedgerPath
  Path to input ledger. Defaults to live ledger.
  
.PARAMETER ConfigPath
  Path to autonomy config.
  
.OUTPUTS
  JSON { effective_mode, reason, enforce: { enqueue_allowed, post_allowed } }
#>

param(
    [string]$LedgerPath = "D:\Infinite\Infinity\Runtime\Receipts\Receipt_Ledger.jsonl",
    [string]$ConfigPath = "D:\Infinite\Infinity\Runtime\Autonomy\autonomy_config.json"
)

# Default Safe State
$rec = [ordered]@{
    effective_mode = "PROPOSE_ONLY"
    reason         = "init_default"
    enforce        = @{
        enqueue_allowed = $false
        post_allowed    = $false
    }
    scan_meta      = @{
        ledger_path    = $LedgerPath
        window_minutes = 60
    }
}

if (-not (Test-Path $ConfigPath)) {
    $rec.reason = "config_missing"
    $rec | ConvertTo-Json -Compress
    return
}

try {
    $config = Get-Content $ConfigPath -Raw | ConvertFrom-Json
    $windowMins = $config.constraints.circuit_breaker_window_minutes
    $codes = $config.constraints.circuit_breaker_error_codes
    $rec.scan_meta.window_minutes = $windowMins
    
    if (-not (Test-Path $LedgerPath)) {
        # Empty ledger = Nominal state (assuming Auth is separate check)
        $rec.effective_mode = "ENQUEUE" # Default from config usually, but falling back to ENQUEUE if no history
        if ($config.autonomy_mode) { $rec.effective_mode = $config.autonomy_mode }
        
        $rec.reason = "clean_ledger"
        $rec.enforce.enqueue_allowed = $true
        $rec.enforce.post_allowed = $true
        
        $rec | ConvertTo-Json -Compress
        return
    }
    
    $since = (Get-Date).AddMinutes(-$windowMins).ToUniversalTime()
    
    # Robust Line-by-Line Scan
    $lines = Get-Content $LedgerPath -Tail 200
    
    $trip = $false
    $tripReason = ""
    $tripCorr = ""
    
    # Invariant: Circuit Breaker (Breaker Logic - Existing)
    # ... (Keep existing scan logic, we need to add Campaign counting here)
    
    $campaignCounts = @{} 
    
    foreach ($line in $lines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $entry = $null
        try { $entry = $line | ConvertFrom-Json } catch { continue }
        
        if (-not $entry -or -not $entry.ts) { continue }
        
        $ts = $null
        try { $ts = [DateTimeOffset]::Parse([string]$entry.ts).ToUniversalTime() } catch { continue }
        
        if ($ts -lt $since) { continue }
        
        # Track Campaign Usage (ATTEMPT receipts for specific intent patterns)
        # Simple heuristic: if intent_id matches known campaign pattern or map. 
        # For V1: We count ALL ATTEMPTS as "autonomy spend" if we wanted global rate limit.
        # Specific Campaign: We need input param or regex? 
        # Better: T34 takes optional -CampaignId filter? No, T34 is global mode.
        # We output the ledger stats and let T35 decide? 
        # No, T34 should enforce "Global Autonomy Budget".
        # Let's count "ATTEMPTS".
        if ($entry.type -eq "ATTEMPT") {
            if ($entry.intent_id) { $campaignCounts[$entry.intent_id] = 1 + $campaignCounts[$entry.intent_id] }
        }

        # Circuit Breaker Logic
        if ($entry.type -eq "RECEIPT" -and $entry.receipt) {
            $r = $entry.receipt
            $http = $null
            try { $http = [int]$r.http_status } catch { $http = $null }
            
            $status = $null; if ($r.PSObject.Properties.Name -contains "status") { $status = [string]$r.status }
            $reason = $null; if ($r.PSObject.Properties.Name -contains "reason") { $reason = [string]$r.reason }
            
            # 1. HTTP Code Match
            if ($http -in $codes) { 
                $trip = $true
                $tripReason = "http_$http"
                $tripCorr = $entry.corr_id
            }
            
            # 2. String Match (Fallback)
            if (-not $trip -and $status -eq "rejected" -and $reason -match "429") {
                $trip = $true
                $tripReason = "rejected_429_match"
                $tripCorr = $entry.corr_id
            }
        }
        
        if ($trip) { break }
    }
    
    $rec.metrics = @{
        attempts_in_window = $campaignCounts.Count
        window_minutes     = $windowMins
    }
    
    if ($trip) {
        $rec.effective_mode = "PROPOSE_ONLY"
        $rec.reason = "circuit_breaker_active: $tripReason ($tripCorr)"
        $rec.enforce.enqueue_allowed = $false
        $rec.enforce.post_allowed = $false
    }
    else {
        # Nominal
        $rec.effective_mode = if ($config.autonomy_mode) { $config.autonomy_mode } else { "ENQUEUE" }
        $rec.reason = "nominal"
        
        # Policy Fix: Enqueue Allowed if Not Propose Only
        $rec.enforce.enqueue_allowed = ($rec.effective_mode -ne "PROPOSE_ONLY")
        
        # Policy Fix: Post Allowed = Enqueue Allowed AND Executor Budget (for now same)
        $rec.enforce.post_allowed = $rec.enforce.enqueue_allowed
    }

}
catch {
    $rec.effective_mode = "PROPOSE_ONLY"
    $rec.reason = "engine_exception: $_"
    $rec.enforce.enqueue_allowed = $false
}

$rec | ConvertTo-Json -Compress
