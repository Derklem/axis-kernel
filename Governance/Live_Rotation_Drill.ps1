# Live_Rotation_Drill.ps1
# Performs Step 1-4 of the Phase 35 Rotation Drill for system:tester.

$Root = "D:\Infinite\Infinity"
$LedgerPath = "$Root\Truth_Engine\revocation_ledger.jsonl"
$KeyringPath = "$Root\Truth_Engine\keyring.json"
$RegistryPath = "$Root\Truth_Engine\identity_registry.json"

$ErrorActionPreference = "Stop"

# --- Hardened Helpers ---
function Escape-JsonString([string]$s) {
    if ($null -eq $s) { return "" }
    $s = $s -replace '\\', '\\\\' -replace '"', '\"' -replace "`r", '\r' -replace "`n", '\n' -replace "`t", '\t'
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

function Hash([string]$s) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return "sha256:" + ([BitConverter]::ToString($hash) -replace "-", "").ToLower()
}

# 1. Verification Before Revocation (v4 check)
Write-Host "--- Step 1: Pre-Revocation State ---"
$kr = Get-Content $KeyringPath -Raw | ConvertFrom-Json
$v4 = $kr.keys | Where-Object { $_.key_id -eq "k_system_tester_v4" }
if (-not $v4) { Write-Error "v4 key missing in keyring!" }
Write-Host "v4 Key Found and Active."

# 2. Revoke v3
Write-Host "--- Step 2: Revoking v3 ---"
$lines = @(Get-Content $LedgerPath | Where-Object { $_ -match '^{.*}' })
$prevHash = $null
for ($i = $lines.Count - 1; $i -ge 0; $i--) {
    try {
        $entry = $lines[$i] | ConvertFrom-Json
        if ($entry.hash) { $prevHash = $entry.hash; break }
    }
    catch {}
}
if (-not $prevHash) { Write-Error "No PrevHash found in ledger!" }

$ts = (Get-Date).ToUniversalTime().ToString("o")
$eid = "rev-" + [Guid]::NewGuid().ToString().Substring(0, 8)
$event = @{
    schema = "axis.revocation.event.v1"; ts_utc = $ts; event_id = $eid; 
    event_type = "KEY_REVOKED"; prev_hash = $prevHash; 
    signed_by = "system:operator"; reason = "Rotation to v4 Drill"; key_id = "k_system_tester_v3"
}

$core = Build-RevocationEventJson $event
$h = Hash $core
$final = $core.TrimEnd("}") + ',"hash":"' + (Escape-JsonString $h) + '"}'

# Append correctly
$final | Out-File $LedgerPath -Append -Encoding utf8
Write-Host "Revocation Event Appended: $eid (Hash $h)"

# 3. Final Verification
Write-Host "--- Step 3: Verification ---"
& "$Root\Governance\Axis_Verify_KeyLifecycleChain.ps1" -Root $Root
if ($LASTEXITCODE -ne 0) { Write-Error "Verification Failed!" }
Write-Host "--- SUCCESS: Drill Complete ---" -ForegroundColor Green
