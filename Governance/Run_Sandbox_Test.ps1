$Root = "D:\Infinite\Infinity_Sandbox"
$Source = "D:\Infinite\Infinity"

# 1. Clean Sandbox
if (Test-Path $Root) { Remove-Item $Root -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Path $Root -Force
New-Item -ItemType Directory -Path (Join-Path $Root "Truth_Engine") -Force
New-Item -ItemType Directory -Path (Join-Path $Root "Governance") -Force

# 2. Copy hardening scripts
$scripts = @(
    "Seed_Ledger_For_Rotation.ps1",
    "Axis_Log_Rotation.ps1",
    "Axis_Anchor_Manager.ps1",
    "Axis_Snapshot_Manager.ps1",
    "Axis_Verify_Replay.ps1"
)
foreach ($s in $scripts) {
    Copy-Item (Join-Path $Source "Governance\$s") (Join-Path $Root "Governance\$s")
}

# 3. RUN SEQUENCE
Write-Output "--- SANDBOX TEST START ---"
& (Join-Path $Root "Governance\Seed_Ledger_For_Rotation.ps1") -Root $Root
& (Join-Path $Root "Governance\Axis_Log_Rotation.ps1") -Root $Root
& (Join-Path $Root "Governance\Axis_Anchor_Manager.ps1") -Force -Root $Root
& (Join-Path $Root "Governance\Axis_Snapshot_Manager.ps1") -Root $Root
& (Join-Path $Root "Governance\Axis_Verify_Replay.ps1") -Root $Root
Write-Output "--- SANDBOX TEST END ---"
