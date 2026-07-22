$Root = "D:\Infinite\Infinity"
$RuntimeDir = Join-Path $Root "Runtime\Decision"
$SnapshotDir = Join-Path $RuntimeDir "Triage_Snapshots"
if (-not (Test-Path $SnapshotDir)) { New-Item $SnapshotDir -ItemType Directory -Force | Out-Null }

$ts = (Get-Date).ToString("yyyyMMdd-HHmmss")
$target = Join-Path $SnapshotDir "Triage_$ts"
New-Item $target -ItemType Directory -Force | Out-Null

Copy-Item (Join-Path $RuntimeDir "decision_log.jsonl") $target
Copy-Item (Join-Path $RuntimeDir "execution_state.json") $target
Copy-Item (Join-Path $RuntimeDir "system_mode.json") $target
Copy-Item (Join-Path $Root "Governance\policy_update_ledger.jsonl") $target

Write-Host "Triage Snapshot Saved to: $target"
