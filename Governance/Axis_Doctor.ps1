
# Axis_Doctor.ps1
# Phase 48: Diagnostic Utility - "Triage Bundle Generator"
# Collects critical system state, logs, and manifests for off-line debugging.

param(
    [string]$Root = "D:\Infinite\Infinity"
)

$ErrorActionPreference = "Stop"
$ReportDir = Join-Path $Root "Reports"
if (-not (Test-Path $ReportDir)) { New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null }

$timestamp = (Get-Date).ToString("yyyyMMdd_HHmm")
$bundleDir = Join-Path $ReportDir "Triage_$timestamp"
New-Item -ItemType Directory -Path $bundleDir -Force | Out-Null

Write-Host "--- AXIS DOCTOR (Triage) ---" -ForegroundColor Cyan
Write-Host "Collecting artifacts to: $bundleDir"

# 1. Logs
Write-Host "  Collecting logs..."
$logFiles = @(
    "Governance\error.log",
    "Governance\verification_log.txt",
    "Governance\verifier.log",
    "Governance\policy_fail.log"
)
foreach ($f in $logFiles) {
    if (Test-Path (Join-Path $Root $f)) {
        Copy-Item (Join-Path $Root $f) $bundleDir
    }
}

# 2. Manifests & Ledgers (Heads only for large ones?)
Write-Host "  Collecting manifests..."
$manifestFiles = @(
    "Governance\state_vector_manifest.json",
    "Memory\packs\compaction_manifest.jsonl",
    "Governance\integrity_pulse_ledger.jsonl",
    "Governance\external_anchor_ledger.jsonl"
)
foreach ($f in $manifestFiles) {
    $src = Join-Path $Root $f
    if (Test-Path $src) {
        $dest = Join-Path $bundleDir (Split-Path $f -Leaf)
        # If huge, maybe just tail? For now, copy full (manifests are smallish).
        # External anchor/pulse might grow. Let's start with full copy.
        Copy-Item $src $dest
    }
}

# 3. Alerts
$AlertDir = Join-Path $Root "Memory\alerts"
if (Test-Path $AlertDir) {
    Copy-Item $AlertDir $bundleDir -Recurse
}

# 4. System Status Snapshot
Write-Host "  Running Axis_Status..."
try {
    & (Join-Path $Root "Governance\Axis_Status.ps1") | Out-File (Join-Path $bundleDir "status_snapshot.txt")
} catch {
    Write-Warning "  Could not run Axis_Status.ps1"
}

# 5. Compress
$zipPath = Join-Path $ReportDir "Triage_Bundle_$timestamp.zip"
Write-Host "  Compressing to $zipPath ..."
Compress-Archive -Path "$bundleDir\*" -DestinationPath $zipPath -Force

# Cleanup temp dir
Remove-Item $bundleDir -Recurse -Force

Write-Host "  [OK] Triage Bundle Ready: $zipPath" -ForegroundColor Green
Return $zipPath
