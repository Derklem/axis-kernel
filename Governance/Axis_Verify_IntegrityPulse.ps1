# Axis_Verify_IntegrityPulse.ps1
# Phase 44.1: Cryptographic verification of the Integrity Pulse chain (byte-faithful)

$ErrorActionPreference = "Stop"

$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$PulseLedger = Join-Path $GovDir "integrity_pulse_ledger.jsonl"

Write-Host "--- VERIFYING INTEGRITY PULSE CHAIN ---" -ForegroundColor Cyan

if (-not (Test-Path $PulseLedger)) {
    Write-Error "Pulse ledger not found: $PulseLedger"
    exit 1
}

$lines = [System.IO.File]::ReadAllLines($PulseLedger)

if ($lines.Count -eq 0) {
    Write-Warning "Pulse ledger is empty: $PulseLedger"
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
    # The 'hash' property is appended last in the watchdog: ,"hash":"..."}
    # Matches exactly how ConvertTo-Json -Compress appends the last property
    return [regex]::Replace($RawLine, ',\s*"hash":"[0-9a-fA-F]+"(?=\s*\})', '')
}

$lastHash = ""
$idx = 0
$verified = 0

foreach ($raw in $lines) {
    if ([string]::IsNullOrWhiteSpace($raw)) { continue }
    
    $entry = $raw | ConvertFrom-Json
    $pulseId = $entry.pulse_id
    
    # 1. Chain Continuity
    if ($idx -gt 0 -and $entry.previous_hash -ne $lastHash) {
        Write-Host "[FAIL] Chain Break at Pulse $pulseId (Expected: $lastHash, Found: $($entry.previous_hash))" -ForegroundColor Red
        exit 1
    }

    # 2. Hash Verification (Byte-Faithful)
    $receivedHash = $entry.hash
    if ($null -eq $receivedHash -or $receivedHash -eq "") {
        if ($entry.mode -ne "GENESIS") {
            Write-Host "[FAIL] Missing hash at Pulse $pulseId" -ForegroundColor Red
            exit 1
        }
    }
    else {
        $payloadRaw = Strip-HashFieldFromRawLine -RawLine $raw
        $computedHash = Compute-Sha256Hex -Text $payloadRaw

        if ($computedHash -ne $receivedHash) {
            Write-Host "[FAIL] Hash Mismatch at Pulse $pulseId" -ForegroundColor Red
            Write-Host "  Computed: $computedHash"
            Write-Host "  Received: $receivedHash"
            exit 1
        }
    }

    # 3. Status Check
    if ($entry.status -ne "SUCCESS" -and $entry.mode -ne "GENESIS") {
        Write-Host "[WARN] Pulse $pulseId reported FAIL" -ForegroundColor Yellow
        foreach ($c in $entry.components) {
            if ($c.status -ne "SUCCESS") {
                Write-Host "  -> Component '$($c.name)' failed with exit code $($c.exit_code)" -ForegroundColor Red
            }
        }
    }

    $lastHash = $receivedHash
    $idx++
    $verified++
}

Write-Host "[OK] Pulse Chain Verified ($verified pulses)." -ForegroundColor Green
exit 0
