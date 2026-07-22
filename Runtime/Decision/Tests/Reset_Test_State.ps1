# Reset_Test_State.ps1
# Cleans the environment for a fresh kill-test run.

$RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$GovDir = "D:\Infinite\Infinity\Governance"

$FilesToClear = @(
    "$RuntimeDir\execution_state.json",
    "$RuntimeDir\queue_cursor.json",
    "$RuntimeDir\intent_queue.jsonl",
    "$RuntimeDir\approved_intents.jsonl",
    "$RuntimeDir\decision_log.jsonl",
    "$RuntimeDir\Tests\killtest_effects.jsonl",
    "D:\Infinite\Infinity\Truth_Engine\spend_ledger.jsonl",
    "D:\Infinite\Infinity\Truth_Engine\receipt_ledger.jsonl",
    "$GovDir\Sovereign_Audit_Ledger.jsonl"
)

foreach ($f in $FilesToClear) {
    if (Test-Path $f) {
        Write-Host "Removing $f" -ForegroundColor Gray
        Remove-Item $f -Force
    }
}

Write-Host "Reset Complete." -ForegroundColor Green
