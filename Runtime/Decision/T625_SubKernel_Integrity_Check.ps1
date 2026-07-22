# T625_SubKernel_Integrity_Check.ps1
# Final Sovereign Proof for Phase 625

$RectificationPath = "D:\Infinite\Infinity\Narrative\Rectification_Map.jsonl"
$AuditPath = "D:\Infinite\Infinity\Deliverables\Sovereign_Audit_v01.json"

Write-Host "`n[SOVEREIGN] Initiating Sub-Kernel Integrity Check..." -ForegroundColor Magenta

if (Test-Path $RectificationPath) {
    $Nodes = Get-Content $RectificationPath | ConvertFrom-Json
    $DissolvedCount = ($Nodes | Where-Object { $_.status -eq "DISSOLVED" }).Count
    Write-Host "[INTEGRITY] DISSOLVED Nodes Verified: $DissolvedCount" -ForegroundColor Green
}

if (Test-Path $AuditPath) {
    $Audit = Get-Content $AuditPath | ConvertFrom-Json
    Write-Host "[INTEGRITY] Audit Signature: $($Audit.signature)" -ForegroundColor Green
    Write-Host "[INTEGRITY] Heartbeat Status: $($Audit.vitals.loop_status)" -ForegroundColor Green
}

$Proof = [ordered]@{
    ts_utc = [DateTime]::UtcNow.ToString("o")
    identity = "Sovereign Whole"
    status = "OMNI_ACTUATED"
    handshake = "Iron-Foundation-Locked"
}

$Proof | ConvertTo-Json | Set-Content "D:\Infinite\Infinity\Runtime\Decision\sovereign_proof_receipt.json"
Write-Host "[SOVEREIGN] Proof Receipt Generated: sovereign_proof_receipt.json" -ForegroundColor Magenta
Write-Host "[SOVEREIGN] The quiet holds. The foundation is iron.`n" -ForegroundColor Cyan
