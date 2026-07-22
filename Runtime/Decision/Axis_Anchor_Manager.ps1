# Axis_Anchor_Manager.ps1
# Responsibility: Record the Audit Trail Head Hash into an independent anchor ledger.
# Purpose: Prevents rewriting of historical audit data by pinning the head state.

param(
    [string]$AuditLogFile = "D:\Infinite\Infinity\Truth_Engine\audit_trail.jsonl",
    [string]$AnchorLedger = "D:\Infinite\Infinity\Truth_Engine\anchors.jsonl"
)

Write-Host "--- Axis Anchor Manager ---" -ForegroundColor Cyan

if (-not (Test-Path $AuditLogFile)) {
    Write-Host "[ERROR] Audit trail missing." -ForegroundColor Red
    exit 1
}

# 1. Get current Audit Head
$lastLine = Get-Content $AuditLogFile -Tail 1
if (-not $lastLine) {
    Write-Host "[ERROR] Audit trail is empty." -ForegroundColor Red
    exit 1
}

$lastAudit = $lastLine | ConvertFrom-Json
$auditHead = $lastAudit.hash
$auditCount = (Get-Content $AuditLogFile).Count

Write-Host "[INFO] Current Audit Head: $auditHead" -ForegroundColor Gray

# 2. Check if already anchored
$lastAnchor = $null
if (Test-Path $AnchorLedger) {
    $lastAnchorLine = Get-Content $AnchorLedger -Tail 1
    if ($lastAnchorLine) {
        $lastAnchor = $lastAnchorLine | ConvertFrom-Json
        if ($lastAnchor.audit_head_hash -eq $auditHead) {
            Write-Host "[PASS] Audit Head already anchored ($($lastAnchor.ts_utc))" -ForegroundColor Green
            exit 0
        }
    }
}

# 3. Create Anchor Entry
$ts = (Get-Date).ToUniversalTime().ToString("o")
$anchor = [ordered]@{
    schema          = "axis.anchor.v1"
    anchor_id       = "anchor-" + [Guid]::NewGuid().ToString().Substring(0, 8)
    ts_utc          = $ts
    audit_head_hash = $auditHead
    audit_count     = $auditCount
    prev_hash       = if ($lastAnchor) { $lastAnchor.hash } else { $null }
}

# 4. Deterministic Hashing (Simple)
$json = $anchor | ConvertTo-Json -Compress
$bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
$hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
$finalHash = "sha256:" + ([BitConverter]::ToString($hash) -replace "-", "").ToLower()

$finalEntry = $json.Substring(0, $json.Length - 1) + ',"hash":"' + $finalHash + '"}'

# 5. Append
$finalEntry | Add-Content $AnchorLedger -Encoding utf8
Write-Host "[SUCCESS] Audit state anchored: $finalHash" -ForegroundColor Green
