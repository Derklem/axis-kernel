[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity",
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$failures = 0
$warnings = 0

function Report-Result([string]$Level, [string]$Message) {
    switch ($Level) {
        "PASS" { Write-Output "[PASS] $Message" }
        "FAIL" { Write-Output "[FAIL] $Message"; $script:failures++ }
        "WARN" { Write-Output "[WARN] $Message"; $script:warnings++ }
        "INFO" { Write-Output "[INFO] $Message" }
    }
}

Write-Output "--- T17 Memory Indexer Verification ---"

$MemRoot = Join-Path $Root "Memory"
$StateFile = Join-Path $MemRoot "state\t17_state.json"
# T17 indexes the Provenance Log in Runtime\Decision
$LedgerFile = Join-Path $Root "Runtime\Decision\provenance_events.jsonl"
$SealFile = Join-Path $MemRoot "ledger\segment_seals.jsonl"
$ErrorFile = Join-Path $MemRoot "ledger\ingest_errors.jsonl"

# 1. State Integrity
if (Test-Path $StateFile) {
    try {
        $state = Get-Content $StateFile -Raw | ConvertFrom-Json
        if ($state.last_offset -ge 0) {
            Report-Result "PASS" "T17 State Offset Sanity ($($state.last_offset))"
        }
        else {
            Report-Result "FAIL" "Negative Offset in State: $($state.last_offset)"
        }
    }
    catch {
        Report-Result "FAIL" "Corrupt T17 State File: $_"
    }
}
else {
    Report-Result "WARN" "T17 State File not found (Clean System?)"
}

# 2. Ledger Sanity
if (Test-Path $LedgerFile) {
    $len = (Get-Item $LedgerFile).Length
    if ($len -gt 0) {
        Report-Result "PASS" "Memory Ledger Exists ($len bytes)"
        
        # Offset Bounds Check
        if ($state -and $state.last_offset -gt $len) {
            Report-Result "FAIL" "State Offset ($($state.last_offset)) > Ledger Length ($len)"
        }
        elseif ($state) {
            Report-Result "PASS" "Offset within bounds"
        }
    }
    else {
        Report-Result "WARN" "Memory Ledger is empty"
    }
}
else {
    Report-Result "WARN" "Memory Ledger not found"
}

# 3. Segment Seals (Latest)
if (Test-Path $SealFile) {
    try {
        $lastSeal = Get-Content $SealFile -Tail 1 | ConvertFrom-Json
        if ($lastSeal) {
            $segPath = Join-Path $MemRoot "ledger\$($lastSeal.file)"
            if (Test-Path $segPath) {
                $hash = (Get-FileHash -Path $segPath -Algorithm SHA256).Hash
                if ($hash -eq $lastSeal.sha256) {
                    Report-Result "PASS" "Latest Segment Seal Verified ($($lastSeal.file))"
                }
                else {
                    Report-Result "FAIL" "Segment Seal Mismatch! Expected: $($lastSeal.sha256) Got: $hash"
                }
            }
            else {
                Report-Result "WARN" "Sealed Segment File Missing: $($lastSeal.file)"
            }
        }
    }
    catch {
        Report-Result "FAIL" "Error verifying seals: $_"
    }
}

# 4. Ingest Errors (Quality)
if (Test-Path $ErrorFile) {
    $errCount = (Get-Content $ErrorFile | Measure-Object).Count
    if ($errCount -gt 0) {
        if ($Strict) {
            Report-Result "FAIL" "Ingest Errors Detected ($errCount)"
        }
        else {
            Report-Result "WARN" "Ingest Errors Detected ($errCount)"
        }
    }
    else {
        Report-Result "PASS" "No Ingest Errors"
    }
}

Write-Output "AXIS_VERIFY_RESULT failures=$failures warnings=$warnings"
exit $failures
