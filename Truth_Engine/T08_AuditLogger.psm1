# T08_AuditLogger.psm1
# Authoritative Audit Trail Logger for Axis.
# Records every authorization decision with deterministic JSON and hash chaining.

$ModuleDir = Split-Path $MyInvocation.MyCommand.Path
$AuditLogFile = Join-Path $ModuleDir "audit_trail.jsonl"
$LockFile = $AuditLogFile + ".lock"

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

function Build-AuditEventJson([hashtable]$e) {
    # Canonical property order:
    # schema, ts_utc, event_id, corr_id, intent_id, identity, key_id, op_key, result, result_code, detail, prev_hash, hashes
    
    $s_schema = Escape-JsonString $e.schema
    $s_ts = Escape-JsonString $e.ts_utc
    $s_eid = Escape-JsonString $e.event_id
    $s_cid = Escape-JsonString $e.corr_id
    $s_iid = Escape-JsonString $e.intent_id
    $s_id = Escape-JsonString $e.identity
    $s_kid = Escape-JsonString $e.key_id
    $s_op = Escape-JsonString $e.op_key
    $s_res = Escape-JsonString $e.result
    $s_rescode = Escape-JsonString $e.result_code
    
    # Detail sub-object
    $detailJson = "{}"
    if ($e.detail -and $e.detail.Count -gt 0) {
        $detailParts = @()
        foreach ($k in $e.detail.Keys | Sort-Object) {
            $v = Escape-JsonString ($e.detail[$k])
            $detailParts += '"' + (Escape-JsonString $k) + '":"' + $v + '"'
        }
        $detailJson = "{" + ($detailParts -join ",") + "}"
    }

    $s_prev = if ($null -eq $e.prev_hash) { "null" } else { '"' + (Escape-JsonString $e.prev_hash) + '"' }
    
    # Hashes sub-object (deterministic order)
    $h = $e.hashes
    $s_reg = Escape-JsonString $h.registry
    $s_key = Escape-JsonString $h.keyring
    $s_rev = Escape-JsonString $h.revocation
    $s_pol = Escape-JsonString $h.policy
    
    $hashesJson = '{"registry":"' + $s_reg + '","keyring":"' + $s_key + '","revocation":"' + $s_rev + '","policy":"' + $s_pol + '"}'

    return '{' +
    '"schema":"' + $s_schema + '",' +
    '"ts_utc":"' + $s_ts + '",' +
    '"event_id":"' + $s_eid + '",' +
    '"corr_id":"' + $s_cid + '",' +
    '"intent_id":"' + $s_iid + '",' +
    '"identity":"' + $s_id + '",' +
    '"key_id":"' + $s_kid + '",' +
    '"op_key":"' + $s_op + '",' +
    '"result":"' + $s_res + '",' +
    '"result_code":"' + $s_rescode + '",' +
    '"detail":' + $detailJson + ',' +
    '"prev_hash":' + $s_prev + ',' +
    '"hashes":' + $hashesJson +
    '}'
}

# --- Genesis Initialization ---

if (-not (Test-Path $AuditLogFile)) {
    $genesis = @{
        schema      = "axis.audit.event.v2"
        ts_utc      = "2026-02-13T21:05:00Z"
        event_id    = "audit-genesis"
        corr_id     = "00000000"
        intent_id   = "00000000"
        identity    = "system:audit"
        key_id      = ""
        op_key      = "genesis"
        result      = "INIT"
        result_code = "AUDIT_TRAIL_INITIALIZED"
        detail      = @{}
        prev_hash   = $null
        hashes      = @{ registry = ""; keyring = ""; revocation = ""; policy = "" }
    }
    $core = Build-AuditEventJson $genesis
    $h = Hash-Sha256Hex $core
    $final = $core.Substring(0, $core.Length - 1) + ',"hash":"' + $h + '"}'
    $final | Set-Content $AuditLogFile -Encoding utf8
}

# --- Main Export ---

function Append-AxisAuditTrail {
    param(
        [Parameter(Mandatory = $true)] [string]$IntentId,
        [Parameter(Mandatory = $true)] [string]$CorrId,
        [Parameter(Mandatory = $true)] [string]$Identity,
        [Parameter(Mandatory = $true)] [string]$KeyId,
        [Parameter(Mandatory = $true)] [string]$OpKey,
        [Parameter(Mandatory = $true)] [string]$Result,     # ALLOW, BLOCK
        [Parameter(Mandatory = $true)] [string]$ResultCode, # Taxonomy code
        [Parameter(Mandatory = $false)] [hashtable]$Detail = @{},
        [Parameter(Mandatory = $true)] [hashtable]$Hashes    # @{ registry; keyring; revocation; policy }
    )

    # 1. Get Prev Hash
    $prevHash = $null
    try {
        if (Test-Path $AuditLogFile) {
            $lastLine = Get-Content $AuditLogFile -Tail 1 -ErrorAction SilentlyContinue
            if ($lastLine) {
                $lastEvent = $lastLine | ConvertFrom-Json
                $prevHash = $lastEvent.hash
            }
        }
    }
    catch { }

    # 2. Build Event
    $ts = (Get-Date).ToUniversalTime().ToString("o")
    $eid = "audit-" + [Guid]::NewGuid().ToString().Substring(0, 8)
    
    $event = @{
        schema      = "axis.audit.event.v2"
        ts_utc      = $ts
        event_id    = $eid
        corr_id     = $CorrId
        intent_id   = $IntentId
        identity    = $Identity
        key_id      = $KeyId
        op_key      = $OpKey
        result      = $Result
        result_code = $ResultCode
        detail      = $Detail
        prev_hash   = $prevHash
        hashes      = $Hashes
    }

    $core = Build-AuditEventJson $event
    $h = Hash-Sha256Hex $core
    $final = $core.Substring(0, $core.Length - 1) + ',"hash":"' + $h + '"}'

    # 3. Append with simple lock
    if (Test-Path $LockFile) { Start-Sleep -Milliseconds 100 } # High-contention wait
    try {
        $PID | Set-Content $LockFile -NoNewline -Force
        $final | Out-File $AuditLogFile -Append -Encoding utf8
    }
    finally {
        Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
    }

    return @{ hash = $h; event_id = $eid }
}

Export-ModuleMember -Function Append-AxisAuditTrail, Build-AuditEventJson, Hash-Sha256Hex
