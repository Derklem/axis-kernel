# Revoke-AxisKey.ps1
# Appends a revocation event to the ledger using deterministic JSON for stable hashing.
# Usage: .\Revoke-AxisKey.ps1 -KeyId "k_system_tester_v3" -Reason "Rotation to v4"

param(
    [Parameter(Mandatory = $true)]
    [string]$KeyId,
    
    [string]$Reason = "Manual Revocation",
    [string]$LedgerPath = "D:\Infinite\Infinity\Truth_Engine\revocation_ledger.jsonl"
)

$ErrorActionPreference = "Stop"

# --- Deterministic Helpers ---

function Escape-JsonString([string]$s) {
    if ($null -eq $s) { return "" }
    $s = $s -replace '\\', '\\\\'
    $s = $s -replace '"', '\"'
    $s = $s -replace "`r", '\r'
    $s = $s -replace "`n", '\n'
    $s = $s -replace "`t", '\t'
    return $s
}

function Build-RevocationEventJson([hashtable]$e) {
    # Fixed property order for canonical hash
    $schema = Escape-JsonString $e.schema
    $ts_utc = Escape-JsonString $e.ts_utc
    $event_id = Escape-JsonString $e.event_id
    $event_type = Escape-JsonString $e.event_type
    $prev_hash = if ($null -eq $e.prev_hash) { "null" } else { '"' + (Escape-JsonString $e.prev_hash) + '"' }
    $signed_by = Escape-JsonString $e.signed_by
    $reason = Escape-JsonString $e.reason
    $key_id = Escape-JsonString $e.key_id

    return '{' +
    '"schema":"' + $schema + '",' +
    '"ts_utc":"' + $ts_utc + '",' +
    '"event_id":"' + $event_id + '",' +
    '"event_type":"' + $event_type + '",' +
    '"prev_hash":' + $prev_hash + ',' +
    '"signed_by":"' + $signed_by + '",' +
    '"reason":"' + $reason + '",' +
    '"key_id":"' + $key_id + '"' +
    '}'
}

function Compute-Sha256Hex([string]$s) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return "sha256:" + ([BitConverter]::ToString($hash) -replace "-", "").ToLower()
}

# --- Main Logic ---

if (-not (Test-Path $LedgerPath)) {
    Write-Error "Revocation ledger not found at $LedgerPath"
    exit 1
}

# 1. Get Previous Hash (Scan tail carefully)
$lines = Get-Content $LedgerPath -Tail 50
$prevHash = $null

for ($i = $lines.Count - 1; $i -ge 0; $i--) {
    try {
        $entry = $lines[$i] | ConvertFrom-Json
        if ($entry.hash) {
            $prevHash = $entry.hash
            break
        }
    }
    catch {}
}

if (-not $prevHash) {
    Write-Error "Could not find last valid hash in ledger tail."
    exit 1
}

# 2. Build Deterministic Event
$ts = (Get-Date).ToUniversalTime().ToString("o")
$eventId = "rev-" + [Guid]::NewGuid().ToString().Substring(0, 8)

$eventCore = @{
    schema     = "axis.revocation.event.v1"
    ts_utc     = $ts
    event_id   = $eventId
    event_type = "KEY_REVOKED"
    prev_hash  = $prevHash
    signed_by  = "system:operator"
    reason     = $Reason
    key_id     = $KeyId
}

$coreJson = Build-RevocationEventJson $eventCore
$hash = Compute-Sha256Hex $coreJson
$finalJson = $coreJson.TrimEnd("}") + ',"hash":"' + (Escape-JsonString $hash) + '"}'

# 3. Safe Append with Lock
$lock = $LedgerPath + ".lock"
if (Test-Path $lock) { 
    Write-Error "Ledger lock present: $lock. Another process is writing?"
    exit 1
}

try {
    $PID | Set-Content $lock -NoNewline -Force
    $finalJson | Out-File -FilePath $LedgerPath -Append -Encoding utf8
    
    Write-Host "SUCCESS: Key $KeyId Revoked." -ForegroundColor Green
    Write-Host "Event:   $eventId"
    Write-Host "Hash:    $hash"
}
finally {
    Remove-Item $lock -Force -ErrorAction SilentlyContinue
}
