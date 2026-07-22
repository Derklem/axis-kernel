[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity",
    [switch]$Strict
)

$ErrorActionPreference = "Stop"

function Report-Result($lvl, $msg) {
    if ($lvl -eq "PASS") { Write-Host "[PASS] $msg" -ForegroundColor Green }
    elseif ($lvl -eq "FAIL") { Write-Host "[FAIL] $msg" -ForegroundColor Red; exit 1 }
    elseif ($lvl -eq "WARN") { Write-Host "[WARN] $msg" -ForegroundColor Yellow }
    else { Write-Host "[$lvl] $msg" -ForegroundColor Gray }
}

$RuntimeDir = Join-Path $Root "Runtime\Decision"
$LedgerFile = Join-Path $RuntimeDir "promotion_ledger.jsonl"
$QueueFile = Join-Path $RuntimeDir "intent_queue.jsonl" # Audit Main Queue primarily

if (-not (Test-Path $LedgerFile)) {
    Report-Result "WARN" "Promotion Ledger not found (New system?)"
    exit 0
}

# 1. Load Queue State (Ground Truth)
$queueNonces = @{}
if (Test-Path $QueueFile) {
    $qLines = Get-Content $QueueFile
    foreach ($line in $qLines) {
        try {
            $e = $line | ConvertFrom-Json
            if ($e.nonce) { $queueNonces[$e.nonce] = $true }
        }
        catch {}
    }
}

# 2. Load Decision Log State (Execution Proof)
$executedNonces = @{}
$DecisionLog = Join-Path $RuntimeDir "decision_log.jsonl"
$Archives = Get-ChildItem -Path $RuntimeDir -Filter "decision_log_archive_*.jsonl" 

$logFiles = @($DecisionLog) + $Archives.FullName

foreach ($f in $logFiles) {
    if (Test-Path $f) {
        # Optimization: Just regex match "intent_id":"..." or "nonce":"..."
        # But JSON parse is safer. Using regex for speed on large logs?
        # Let's use simple line scanning for now.
        $lines = Get-Content $f -ErrorAction SilentlyContinue 
        foreach ($ln in $lines) {
            if ($ln -match '"intent_id"\s*:\s*"([^"]+)"') {
                $executedNonces[$matches[1]] = $true
            }
        }
    }
}

# 3. Verify Ledger
$lLines = Get-Content $LedgerFile
$seenNonces = @{}
$errors = 0

foreach ($line in $lLines) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
        $entry = $line | ConvertFrom-Json
        
        # A. Structure Check
        if (-not ($entry.nonce -and $entry.ts -and $entry.source)) {
            Report-Result "FAIL" "Invalid Promotion Ledger Entry: $line"
        }
        
        # B. Anti-Replay (Internal Consistency)
        if ($seenNonces.ContainsKey($entry.nonce)) {
            Report-Result "FAIL" "Duplicate Promotion detected in Ledger! Nonce: $($entry.nonce)"
        }
        $seenNonces[$entry.nonce] = $true
        
        # C. Causal Link (Ledger -> Queue -> Execution)
        # Verify that if we said we promoted it to intent_queue, it exists there OR has been executed/archived.
        $targetReached = $false
        
        # 1. Check Active Queue
        if ($queueNonces.ContainsKey($entry.nonce)) {
            $targetReached = $true
        }
        
        # 2. Check Decision Log (Executed)
        if (-not $targetReached) {
            # Lazy load decision logs if needed (optimization: load indicies once at start)
            # For now, just checking the loaded list if we were to load it, but since we didn't load it above, let's fix that structure.
            # We should load executed nonces once.
        }
        # Note: T08 might archive/delete from queue? If so, this check needs to search archives.
        # For Phase 27, we assume active queue or loose coupling.
        # Let's check strictness. If strict, we demand it.
        
        # C. Causal Link (Ledger -> Queue -> Execution)
        if ($entry.target -eq "intent_queue") {
            $found = ($queueNonces.ContainsKey($entry.nonce) -or $executedNonces.ContainsKey($entry.nonce))
            
            if (-not $found) {
                # If strict, this is a failure (Promoted but vanished)
                if ($Strict) {
                    Report-Result "FAIL" "Promoted nonce vanished (Not in Queue, Log, or Archive): $($entry.nonce)"
                }
                else {
                    Report-Result "WARN" "Promoted nonce missing from active set (check pending/archives): $($entry.nonce)"
                }
            }
        }
    }
    catch {
        Report-Result "FAIL" "Ledger Parse Error: $_"
    }
}

Report-Result "PASS" "Promoter Chain Verified ($($seenNonces.Count) promotions)"
exit 0
