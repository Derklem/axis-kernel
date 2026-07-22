# Verify_Phase43.ps1
$ErrorActionPreference = "Continue"

$LogPath = "D:\Infinite\Infinity\Governance\phase43_transcript.log"
Start-Transcript -Path $LogPath -Append

function Log($msg) { Write-Host "  >> $msg" -ForegroundColor Gray }

try {
    $Root = "D:\Infinite\Infinity"
    $MemoryRoot = Join-Path $Root "Memory"
    $TruthDir = Join-Path $Root "Truth_Engine"
    $GovDir = Join-Path $Root "Governance"

    Write-Host "--- Phase 43 Verification Start ---" -ForegroundColor Cyan

    # 1. CLEAN SLATE
    Log "Cleaning Memory..."
    Remove-Item (Join-Path $MemoryRoot "cursors") -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item (Join-Path $MemoryRoot "indexes") -Recurse -Force -ErrorAction SilentlyContinue 
    Remove-Item (Join-Path $MemoryRoot "ledger") -Recurse -Force -ErrorAction SilentlyContinue

    # 2. SEED
    Log "Seeding Ledgers..."
    & (Join-Path $GovDir "Seed_Ledger_For_Rotation.ps1")

    # 3. INGEST (Initial)
    Log "Importing T17..."
    Import-Module (Join-Path $TruthDir "T17_MemoryIndexer.psm1") -Force
    Log "Running Update-MemoryLedger..."
    Update-MemoryLedger -MemoryRoot $MemoryRoot

    # Check counts
    $auditSeenFile = Join-Path $MemoryRoot "indexes\seen_audit.jsonl"
    if (Test-Path $auditSeenFile) {
        $initialCount = (Get-Content $auditSeenFile | Measure-Object).Count
        Log "Initial Seen Count: $initialCount"
    }
    else {
        Log "WARNING: No seen file found after ingestion!"
        $initialCount = 0
    }

    # 4. ROTATE
    Log "Running Rotation..."
    & (Join-Path $GovDir "Axis_Log_Rotation.ps1")

    # 5. INGEST (Post-Rotation)
    Log "Running Update-MemoryLedger (Post-Rotation)..."
    Update-MemoryLedger -MemoryRoot $MemoryRoot

    # 6. ASSERT
    $success = $true
    $checks = @(
        @{ name = "audit"; expected = 2; file = Join-Path $MemoryRoot "indexes\seen_audit.jsonl" }
        @{ name = "spend"; expected = 2; file = Join-Path $MemoryRoot "indexes\seen_spend.jsonl" }
        @{ name = "decision"; expected = 5; file = Join-Path $MemoryRoot "indexes\seen_decision.jsonl" }
    )

    foreach ($c in $checks) {
        if (Test-Path $c.file) {
            $count = (Get-Content $c.file | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Measure-Object).Count
            Log "Ledger $($c.name): Final Count $count (Expected $($c.expected))"
            if ($count -ne $c.expected) {
                Write-Warning "  FAILURE: Ledger $($c.name) count mismatch! Expected $($c.expected), got $count"
                $success = $false
            }
        }
        else {
            Write-Warning "  FAILURE: Ledger $($c.name) seen file missing!"
            $success = $false
        }
    }

    if ($success) {
        Write-Host "SUCCESS: Phase 43.1 production-ready. No duplicates or gaps detected." -ForegroundColor Green
    }
    else {
        Write-Error "FAILURE: Verification failed for one or more ledgers."
    }

}
catch {
    Write-Host "!!! EXCEPTION !!!" -ForegroundColor Red
    $_ | Format-List -Force
}
finally {
    Stop-Transcript
}

Write-Host "--- Phase 43 Verification End ---" -ForegroundColor Cyan
