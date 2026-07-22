# Fix-GenesisLedger.ps1
function Escape-JsonString([string]$s) {
    if ($null -eq $s) { return "" }
    $s = $s -replace '\\', '\\\\' -replace '"', '\"' -replace "`r", '\r' -replace "`n", '\n' -replace "`t", '\t'
    return $s
}
function Build-RevocationEventJson([hashtable]$e) {
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

$event = @{
    schema = "axis.revocation.event.v1"; ts_utc = "2026-02-13T20:10:00Z"; 
    event_id = "rev-genesis"; event_type = "GENESIS"; prev_hash = $null; 
    signed_by = "system:operator"; reason = "init"; key_id = ""
}

$core = Build-RevocationEventJson $event
$h = Hash $core
$final = $core.TrimEnd("}") + ',"hash":"' + (Escape-JsonString $h) + '"}'
$final | Set-Content "D:\Infinite\Infinity\Truth_Engine\revocation_ledger.jsonl" -Encoding utf8
Write-Host "New Genesis Hash: $h"
