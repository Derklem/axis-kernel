# Seed_Ledger_For_Rotation.ps1
$ErrorActionPreference = "Stop"

$Root = "D:\Infinite\Infinity"
$TruthDir = Join-Path $Root "Truth_Engine"
$GovDir = Join-Path $Root "Governance"

# 0. Clean Archives and Hot Files for Fresh Test
$archives = Get-ChildItem -Path $TruthDir -Filter "Archive" -Directory
if ($archives) { Remove-Item $archives.FullName -Recurse -Force -ErrorAction SilentlyContinue }
New-Item -Path $TruthDir -Name "Archive" -ItemType Directory -Force

$hotFiles = @(
    (Join-Path $TruthDir "audit_trail.jsonl")
    (Join-Path $TruthDir "spend_ledger.jsonl")
    (Join-Path $GovDir "revocation_ledger.jsonl")
    (Join-Path $GovDir "policy_update_ledger.jsonl")
    (Join-Path $Root "Runtime\Decision\decision_log.jsonl")
)
foreach ($f in $hotFiles) {
    if (Test-Path $f) { Remove-Item $f -Force -ErrorAction SilentlyContinue }
}

# --- 1. Seed audit_trail.jsonl ---
$auditPath = Join-Path $TruthDir "audit_trail.jsonl"
$auditContent = @()

$janAuditHash = "sha256:1111111111111111111111111111111111111111111111111111111111111111"
$auditContent += [ordered]@{
    timestamp      = "2026-01-15T12:00:00Z"
    audit_event_id = "audit-jan-01"
    result_code    = "SUCCESS"
    hash           = $janAuditHash
    previous_hash  = "genesis"
} | ConvertTo-Json -Compress

$febAuditHash = "sha256:2222222222222222222222222222222222222222222222222222222222222222"
$auditContent += [ordered]@{
    timestamp      = "2026-02-14T12:00:00Z"
    audit_event_id = "audit-feb-01"
    result_code    = "SUCCESS"
    hash           = $febAuditHash
    previous_hash  = $janAuditHash
} | ConvertTo-Json -Compress

[System.IO.File]::WriteAllLines($auditPath, $auditContent)
Write-Host "Seeded audit_trail.jsonl"

# --- 2. Seed spend_ledger.jsonl ---
$spendPath = Join-Path $TruthDir "spend_ledger.jsonl"
$spendContent = @()

$janSpendHash = "sha256:3333333333333333333333333333333333333333333333333333333333333333"
$spendContent += [ordered]@{
    timestamp     = "2026-01-15T12:00:00Z"
    event_id      = "spend-jan-01"
    type          = "RESERVE"
    hash          = $janSpendHash
    previous_hash = "genesis"
} | ConvertTo-Json -Compress

$febSpendHash = "sha256:4444444444444444444444444444444444444444444444444444444444444444"
$spendContent += [ordered]@{
    timestamp     = "2026-02-14T12:00:00Z"
    event_id      = "spend-feb-01"
    type          = "COMMIT"
    hash          = $febSpendHash
    previous_hash = $janSpendHash
} | ConvertTo-Json -Compress

[System.IO.File]::WriteAllLines($spendPath, $spendContent)
Write-Host "Seeded spend_ledger.jsonl"

# --- 3. Seed policy_update_ledger.jsonl (Genesis) ---
$policyPath = Join-Path $GovDir "policy_update_ledger.jsonl"
$policyHash = "sha256:2e6ab477b1bcb249c321d6fb9c0e09831c4f09883fd3553f79fa525ba0a706e5"
$policyContent = @(
    [ordered]@{
        timestamp     = "2026-01-01T00:00:00Z"
        event_id      = "policy-genesis"
        hash          = $policyHash
        previous_hash = "genesis"
    } | ConvertTo-Json -Compress
)
[System.IO.File]::WriteAllLines($policyPath, $policyContent)
Write-Host "Seeded policy_update_ledger.jsonl"

# --- 4. Seed revocation_ledger.jsonl (Empty but existing) ---
$revPath = Join-Path $GovDir "revocation_ledger.jsonl"
Set-Content -Path $revPath -Value "" -NoNewline
Write-Host "Reset revocation_ledger.jsonl"

# --- 5. Seed decision_log.jsonl (Simulate 5 entries) ---
$decPath = Join-Path $Root "Runtime\Decision\decision_log.jsonl"
$decContent = @()
for ($i = 1; $i -le 5; $i++) {
    $decContent += [ordered]@{
        ts       = (Get-Date).ToString("o")
        event_id = "dec-$i"
        decision = "AUTO_PASS"
    } | ConvertTo-Json -Compress
}
[System.IO.File]::WriteAllLines($decPath, $decContent)
Write-Host "Seeded decision_log.jsonl"


