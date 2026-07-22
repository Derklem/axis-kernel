# Axis_Verify_ExternalAnchors.ps1
# Phase 46: Cryptographic verification of signatures and quorum.

$ErrorActionPreference = "Stop"

$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$TruthDir = Join-Path $Root "Truth_Engine"
$AnchorLedger = Join-Path $GovDir "external_anchor_ledger.jsonl"
$PolicyFile = Join-Path $GovDir "external_anchor_policy.json"
$KeyringFile = Join-Path $TruthDir "keyring.json"

Write-Host "--- VERIFYING EXTERNAL ANCHOR CHAIN (SIGNED) ---" -ForegroundColor Cyan

if (-not (Test-Path $AnchorLedger)) {
    Write-Error "External anchor ledger not found: $AnchorLedger"
    exit 1
}

$policy = Get-Content $PolicyFile | ConvertFrom-Json
$keyring = Get-Content $KeyringFile | ConvertFrom-Json
$lines = [System.IO.File]::ReadAllLines($AnchorLedger)

if ($lines.Count -eq 0) {
    Write-Warning "Anchor ledger is empty: $AnchorLedger"
    exit 0
}

function Compute-Sha256Hex {
    param([string]$Text)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
        return ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "").ToLower()
    }
    finally { $sha.Dispose() }
}

function Strip-HashFieldFromRawLine {
    param([string]$RawLine)
    return [regex]::Replace($RawLine, ',\s*"hash":"[0-9a-fA-F]+"(?=\s*\})', '')
}

$lastHash = ""
$idx = 0
$verified = 0

foreach ($raw in $lines) {
    if ([string]::IsNullOrWhiteSpace($raw)) { continue }
    
    $entry = $raw | ConvertFrom-Json
    $anchorId = $entry.anchor_id
    
    # 1. Chain Continuity
    if ($idx -gt 0 -and $entry.previous_hash -ne $lastHash) {
        Write-Host "[FAIL] Chain Break at Anchor $anchorId (Expected: $lastHash, Found: $($entry.previous_hash))" -ForegroundColor Red
        exit 1
    }

    # 2. Hash Verification (Byte-Faithful)
    $receivedHash = $entry.hash
    if ($null -eq $receivedHash -or $receivedHash -eq "") {
        if ($entry.type -ne "GENESIS") {
            Write-Host "[FAIL] Missing hash at Anchor $anchorId" -ForegroundColor Red
            exit 1
        }
    }
    else {
        $payloadRaw = Strip-HashFieldFromRawLine -RawLine $raw
        $computedHash = Compute-Sha256Hex -Text $payloadRaw

        if ($computedHash -ne $receivedHash) {
            Write-Host "[FAIL] Hash Mismatch at Anchor $anchorId" -ForegroundColor Red
            Write-Host "  Computed: $computedHash"
            Write-Host "  Received: $receivedHash"
            exit 1
        }
    }

    # 3. Signature Verification (Authorship)
    if ($entry.type -ne "GENESIS" -and $entry.signature) {
        $payloadObj = [ordered]@{
            anchor_id = $entry.anchor_id
            ts_utc    = $entry.ts_utc
            basis     = $entry.basis
        }
        $payloadRaw = $payloadObj | ConvertTo-Json -Compress
        
        $keyEntry = $keyring.keys | Where-Object { $_.key_id -eq $entry.key_id }
        if (-not $keyEntry) {
            Write-Host "[FAIL] Signing key not found: $($entry.key_id)" -ForegroundColor Red
            exit 1
        }
        
        & (Join-Path $GovDir "Axis_Verify_Signature.ps1") -Payload $payloadRaw -SignatureBase64 $entry.signature -PublicKeyBase64 $keyEntry.fingerprint
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[FAIL] Signature Invalid at Anchor $anchorId" -ForegroundColor Red
            exit 1
        }
    }

    # 4. Quorum Check
    if ($entry.type -ne "GENESIS") {
        $successCount = ($entry.channels | Where-Object { $_.status -eq "SUCCESS" }).Count
        if ($successCount -lt $policy.required_successes) {
            Write-Host "[FAIL] Quorum Failure at Anchor $anchorId (Successes: $successCount, Required: $($policy.required_successes))" -ForegroundColor Red
            if ($policy.strict_mode) { exit 1 }
        }
    }

    $lastHash = $receivedHash
    $idx++
    $verified++
}

Write-Host "[OK] External Anchor Chain Verified ($verified anchors)." -ForegroundColor Green
exit 0
