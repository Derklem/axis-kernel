# Axis_Spend_Manager.psm1
# Economic Forensics Manager for Axis.
# Tracks resource spend (RESERVE, COMMIT, ROLLBACK) with hash chaining.

$ModuleDir = Split-Path $MyInvocation.MyCommand.Path
$SpendLedger = Join-Path $ModuleDir "spend_ledger.jsonl"
$LockFile = $SpendLedger + ".lock"

# --- Hardened Helpers ---

function Escape-JsonString([string]$s) {
    if ($null -eq $s) { return "" }
    $s = $s -replace '\\', '\\\\' -replace '"', '\"' -replace "`r", '\r' -replace "`n", '\n' -replace "`t", '\t'
    return $s
}

function Hash-Sha256Hex([string]$s) {
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($s)
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return "sha256:" + ([BitConverter]::ToString($hash) -replace "-", "").ToLower()
}

function Build-SpendEventJson([hashtable]$e) {
    # Canonical property order:
    # schema, ts_utc, event_id, corr_id, intent_id, identity, audit_event_id, op_key, type, units, prev_hash
    
    $s_schema = Escape-JsonString $e.schema
    $s_ts = Escape-JsonString $e.ts_utc
    $s_eid = Escape-JsonString $e.event_id
    $s_cid = Escape-JsonString $e.corr_id
    $s_iid = Escape-JsonString $e.intent_id
    $s_id = Escape-JsonString $e.identity
    $s_aeid = Escape-JsonString $e.audit_event_id
    $s_op = Escape-JsonString $e.op_key
    $s_type = Escape-JsonString $e.type
    $s_units = [int]$e.units
    $s_stxn = if ($null -eq $e.spend_txn_id) { "null" } else { '"' + (Escape-JsonString $e.spend_txn_id) + '"' }
    $s_prev = if ($null -eq $e.prev_hash) { "null" } else { '"' + (Escape-JsonString $e.prev_hash) + '"' }

    return '{' +
    '"schema":"' + $s_schema + '",' +
    '"ts_utc":"' + $s_ts + '",' +
    '"event_id":"' + $s_eid + '",' +
    '"corr_id":"' + $s_cid + '",' +
    '"intent_id":"' + $s_iid + '",' +
    '"spend_txn_id":' + $s_stxn + ',' +
    '"identity":"' + $s_id + '",' +
    '"audit_event_id":"' + $s_aeid + '",' +
    '"op_key":"' + $s_op + '",' +
    '"type":"' + $s_type + '",' +
    '"units":' + $s_units + ',' +
    '"prev_hash":' + $s_prev +
    '}'
}

# --- Genesis Initialization ---

if (-not (Test-Path $SpendLedger)) {
    $genesis = @{
        schema         = "axis.spend.event.v1"
        ts_utc         = "2026-02-13T21:05:00Z"
        event_id       = "spend-genesis"
        corr_id        = "00000000"
        intent_id      = "00000000"
        identity       = "system:spend"
        audit_event_id = "audit-genesis"
        op_key         = "genesis"
        type           = "INIT"
        units          = 0
        prev_hash      = $null
    }
    $core = Build-SpendEventJson $genesis
    $h = Hash-Sha256Hex $core
    $final = $core.Substring(0, $core.Length - 1) + ',"hash":"' + $h + '"}'
    $final | Set-Content $SpendLedger -Encoding utf8
}

# --- Main Export ---

function Append-AxisSpendEntry {
    param(
        [Parameter(Mandatory = $true)] [string]$IntentId,
        [Parameter(Mandatory = $true)] [string]$CorrId,
        [Parameter(Mandatory = $true)] [string]$Identity,
        [Parameter(Mandatory = $true)] [string]$AuditEventId,
        [Parameter(Mandatory = $true)] [string]$OpKey,
        [Parameter(Mandatory = $false)] [string]$SpendTxnId,
        [Parameter(Mandatory = $true)] [string]$Type, # RESERVE, COMMIT, ROLLBACK
        [Parameter(Mandatory = $true)] [int]$Units
    )

    # 1. Get Prev Hash
    $prevHash = $null
    try {
        if (Test-Path $SpendLedger) {
            $lastLine = Get-Content $SpendLedger -Tail 1 -ErrorAction SilentlyContinue
            if ($lastLine) {
                $lastEvent = $lastLine | ConvertFrom-Json
                $prevHash = $lastEvent.hash
            }
        }
    }
    catch { }

    # 2. Build Event
    $ts = (Get-Date).ToUniversalTime().ToString("o")
    $eid = "spend-" + [Guid]::NewGuid().ToString().Substring(0, 8)
    
    $event = @{
        schema         = "axis.spend.event.v1"
        ts_utc         = $ts
        event_id       = $eid
        corr_id        = $CorrId
        intent_id      = $IntentId
        identity       = $Identity
        audit_event_id = $AuditEventId
        op_key         = $OpKey
        spend_txn_id   = $SpendTxnId
        type           = $Type
        units          = $Units
        prev_hash      = $prevHash
    }

    $core = Build-SpendEventJson $event
    $h = Hash-Sha256Hex $core
    $final = $core.Substring(0, $core.Length - 1) + ',"hash":"' + $h + '"}'

    # 3. Append with simple lock
    if (Test-Path $LockFile) { Start-Sleep -Milliseconds 100 }
    try {
        $PID | Set-Content $LockFile -NoNewline -Force
        $final | Add-Content $SpendLedger -Encoding utf8
    }
    finally {
        Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
    }

    return $h
}

Export-ModuleMember -Function Append-AxisSpendEntry, Build-SpendEventJson, Hash-Sha256Hex
