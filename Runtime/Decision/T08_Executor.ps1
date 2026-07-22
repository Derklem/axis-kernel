param(
    [switch]$DryRun,
    [string]$IntentFile,
    [string]$TargetProfile = "default",
    [string]$Identity = "generator:axis",
    [string]$KeyId = "PRIMARY",
    [string]$Context = "default"
)

# --- AXIS T08 EXECUTOR BUILD 2026.02.21 ---
$ExecutorBuild = "2026.02.21"

# --- LIBRARIES ---
$FsLib = "D:\Infinite\Axis_FS_Lib.ps1"
if (Test-Path $FsLib) { . $FsLib } else { Write-Error "T08: Critical Library Missing: $FsLib"; exit 1 }

$SpendMgr = "D:\Infinite\Infinity\Truth_Engine\Axis_Spend_Manager.psm1"
if (Test-Path $SpendMgr) { Import-Module $SpendMgr -Force }

# --- CONFIG ---
$RuntimeDir = "D:\Infinite\Infinity\Runtime\Decision"
$StateFile = Join-Path $RuntimeDir "execution_state.json"
$DecLog = Join-Path $RuntimeDir "decision_log.jsonl"
$L0Log = Join-Path $RuntimeDir "L0_Handshake_Ledger.jsonl"
$CursorFile = Join-Path $RuntimeDir "queue_cursor.json"
$Approvals = "D:\Infinite\Infinity\Governance\Review_Log.jsonl"
$QueueFile = Join-Path $RuntimeDir "approved_intents.jsonl"
$Client = "D:\Infinite\Axis_Moltbook_Client.ps1"
$LocalStateFile = Join-Path $RuntimeDir "..\Executor\executor_state.json"

# --- HELPERS ---

function Get-State {
    $s = Get-SafeJson -Path $StateFile
    if ($null -eq $s) { return @{ schema = "axis.execution_state.v0.1"; executed_intents = @(); failed_intents = @(); inflight = @{} } }
    return $s
}
function Save-State($s) { Write-AtomicJson -Path $StateFile -Data $s }

function Append-Audit($intent_id, $corr_id, $identity, $key_id, $op, $decision, $reason, $detail = @{}) {
    $AuditLedger = "D:\Infinite\Infinity\Governance\Sovereign_Audit_Ledger.jsonl"
    $event = [ordered]@{
        ts = (Get-Date).ToUniversalTime().ToString("o"); event_id = "AUDIT-" + [Guid]::NewGuid().ToString("N");
        intent_id = $intent_id; corr_id = $corr_id; identity = $identity; key_id = $key_id; op = $op;
        decision = $decision; reason = $reason; detail = $detail
    }
    if ($DryRun) { return $event.event_id }
    Append-JsonlLine -Path $AuditLedger -Data $event
    return $event.event_id
}

function Reserve-Spend($iid, $cid, $ident, $aeid, $op, $stxn) {
    if (Get-Command Append-AxisSpendEntry -ErrorAction SilentlyContinue) {
        Append-AxisSpendEntry -IntentId $iid -CorrId $cid -Identity $ident -AuditEventId $aeid -OpKey $op -SpendTxnId $stxn -Type "RESERVE" -Units 1 | Out-Null
    }
}
function Commit-Spend($iid, $cid, $ident, $aeid, $op, $stxn) {
    if (Get-Command Append-AxisSpendEntry -ErrorAction SilentlyContinue) {
        Append-AxisSpendEntry -IntentId $iid -CorrId $cid -Identity $ident -AuditEventId $aeid -OpKey $op -SpendTxnId $stxn -Type "COMMIT" -Units 1 | Out-Null
    }
}
function Rollback-Spend($iid, $cid, $ident, $aeid, $op, $stxn) {
    if (Get-Command Append-AxisSpendEntry -ErrorAction SilentlyContinue) {
        Append-AxisSpendEntry -IntentId $iid -CorrId $cid -Identity $ident -AuditEventId $aeid -OpKey $op -SpendTxnId $stxn -Type "ROLLBACK" -Units 1 | Out-Null
    }
}

function Append-DecLog($msg, $id, $reason, $cid = $null, $detail = $null) {
    $entry = [ordered]@{ ts = (Get-Date).ToUniversalTime().ToString("o"); intent_id = $id; corr_id = $cid; decision = $reason; message = $msg; detail = $detail }
    if ($DryRun) { Write-Host "[DryRun] Log: $reason - $msg"; return }
    Append-JsonlLine -Path $DecLog -Data $entry
}

function Block-And-Rollback($reason, $msg, $fx) {
    Append-DecLog $msg $fx.intent_id $reason $fx.corr_id @{ op_key = $fx.op_key }
    Rollback-Spend -iid $fx.intent_id -cid $fx.corr_id -ident $fx.identity -aeid $fx.audit_event_id -op $fx.op_key -stxn $fx.spend_txn_id
}

function Resolve-Submolt($intent) {
    if ($intent.target -is [string]) { if ($intent.target -match '^[^:]+:(.+)$') { return $Matches[1] } }
    try { if ($intent.target.submolt) { return [string]$intent.target.submolt } } catch {}
    return $null
}

function Get-ApprovalStatus($intentId) {
    if (-not (Test-Path $Approvals)) { return "unreviewed" }
    $last = $null
    foreach ($line in (Get-Content $Approvals)) { try { $obj = $line | ConvertFrom-Json; if ($obj.intent_id -eq $intentId) { $last = $obj } } catch {} }
    return if ($null -ne $last) { $last.decision } else { "unreviewed" }
}

# --- MAIN ---
$CycleStats = [ordered]@{ intents_seen = 0; intents_blocked = 0; actuations = 0 }

$t08Lock = Invoke-WithMutex -Name "Global\Axis_T08_Mutex_v2" -TimeoutMs 2000 -ScriptBlock {
    try {
        $state = Get-State
        if (-not $state.inflight) { $state.inflight = @{} }

        # PHASE 1: REAPER (L0 + Stale/Crashed Inflight)
        $keys = @($state.inflight.Keys)
        $l0Logs = if (Test-Path $L0Log) { (Get-Content $L0Log -Tail 500) | ForEach-Object { try { $_ | ConvertFrom-Json } catch {} } } else { @() }
        
        foreach ($iid in $keys) {
            $f = $state.inflight."$iid"; 
            if ($null -eq $f) { continue }
            $c = $f.corr_id
            
            # 1. Check L0 Proof
            $proof = $l0Logs | Where-Object { $_.corr_id -eq $c -and ($_.event_type -in @("client_handshake", "confirmed_post")) } | Select-Object -Last 1
            if ($null -ne $proof) {
                $state.executed_intents += $iid; $state.inflight.Remove($iid)
                Commit-Spend -iid $iid -cid $c -ident $f.identity -aeid $f.audit_event_id -op $f.op -stxn $f.spend_txn_id
                & "D:\Infinite\Infinity\Truth_Engine\T19_ReceiptLedger.ps1" -Action WRITE_RECEIPT -RunId $proof.run_id -CorrId $c -OpType "POST" -Target ($f.op) -ReceiptData @{ status = "confirmed_l0"; pid = $f.pid }
                continue
            }
            
            # 2. Check Crash/Stale (if PID recorded and process is dead)
            if ($f.pid) {
                $proc = Get-Process -Id $f.pid -ErrorAction SilentlyContinue
                if ($null -eq $proc) {
                    # Process died without receipt. Check Receipt Ledger for partial success.
                    $receipt = & "D:\Infinite\Infinity\Truth_Engine\T19_ReceiptLedger.ps1" -Action GET_STATUS -CorrId $c
                    if ($null -ne $receipt -and $receipt.type -eq "RECEIPT") {
                        $state.executed_intents += $iid; $state.inflight.Remove($iid)
                        Commit-Spend -iid $iid -cid $c -ident $f.identity -aeid $f.audit_event_id -op $f.op -stxn $f.spend_txn_id
                    }
                    else {
                        # No receipt found. Move back to failed or remove from inflight so process loop can retry (if cursor allows)
                        Write-Warning "Inflight $iid (Corr: $c) crashed with PID $($f.pid). Removing from inflight."
                        Append-DecLog "Inflight Crash Recovery" $iid "CRASH_RECOVERED" $c @{ pid = $f.pid }
                        $state.inflight.Remove($iid)
                    }
                }
            }
        }
        Save-State $state

        # PHASE 2 & 3: QUEUE PROCESSING (Per-Intent Atomicity)
        $cursor = Get-SafeJson -Path $CursorFile
        if ($null -eq $cursor) { $cursor = @{ byte_offset = 0; line = 0 } }
        
        Write-Host "T08: QueueFile check: $QueueFile" -ForegroundColor Gray
        if (Test-Path $QueueFile) {
            Write-Host "T08: QueueFile exists. Size = $((Get-Item $QueueFile).Length)" -ForegroundColor Gray
            $fs = [System.IO.File]::Open($QueueFile, "Open", "Read", "ReadWrite")
            $fs.Seek($cursor.byte_offset, "Begin") | Out-Null
            $reader = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8)
            
            while (-not $reader.EndOfStream) {
                $line = $reader.ReadLine()
                $currentOffset = $fs.Position
                if ([string]::IsNullOrWhiteSpace($line)) { 
                    Write-AtomicJson -Path $CursorFile -Data @{ byte_offset = $currentOffset; ts_utc = (Get-Date).ToUniversalTime().ToString("o") }
                    continue 
                }
                
                $intent = try { $line | ConvertFrom-Json } catch { 
                    Write-AtomicJson -Path $CursorFile -Data @{ byte_offset = $currentOffset; ts_utc = (Get-Date).ToUniversalTime().ToString("o") }
                    continue 
                }
                
                $cid_raw = if ($null -ne $intent.correlation_id) { $intent.correlation_id } else { $intent.corr_id }
                $cid = if (-not [string]::IsNullOrWhiteSpace($cid_raw)) { [string]$cid_raw } else { "AUTO-" + [guid]::NewGuid().ToString().Substring(0, 8) }
                
                $id_raw = if ($null -ne $intent.intent_id) { $intent.intent_id } else { $intent.nonce }
                $id = if (-not [string]::IsNullOrWhiteSpace($id_raw)) { [string]$id_raw } else { $null }
                
                if ([string]::IsNullOrWhiteSpace($id)) {
                    Write-Warning "T08: Intent at offset $currentOffset has empty ID. Skipping."
                    $currentOffset += $lineLen + $newlineLen
                    continue
                }
                
                # Dedupe
                $receipt = & "D:\Infinite\Infinity\Truth_Engine\T19_ReceiptLedger.ps1" -Action GET_STATUS -CorrId $cid
                if (($null -ne $receipt -and $receipt.type -eq "RECEIPT") -or ($id -in $state.executed_intents) -or ($null -ne $state.inflight) -and ($null -ne $state.inflight.PSObject.Properties[$id])) {
                    Write-AtomicJson -Path $CursorFile -Data @{ byte_offset = $currentOffset; ts_utc = (Get-Date).ToUniversalTime().ToString("o") }
                    continue
                }

                $CycleStats.intents_seen++
                $fx = @{ intent_id = $id; corr_id = $cid; identity = $intent.identity; op_key = "moltbook.post"; spend_txn_id = ("STXN-" + [Guid]::NewGuid().ToString("N").Substring(0, 8)); audit_event_id = "PENDING" }
                
                # INFLIGHT PHASE
                & "D:\Infinite\Infinity\Truth_Engine\T19_ReceiptLedger.ps1" -Action WRITE_ATTEMPT -CorrId $cid -AttemptData @{ status = "inflight"; pid = $PID }
                Reserve-Spend -iid $id -cid $cid -ident $fx.identity -aeid "PENDING" -op $fx.op_key -stxn $fx.spend_txn_id
                
                # Policy/Review
                if ($intent.review.required -and (Get-ApprovalStatus $id) -ne "approved") {
                    Block-And-Rollback -reason "BLOCKED_REVIEW" -msg "Review Required" -fx $fx
                    Write-AtomicJson -Path $CursorFile -Data @{ byte_offset = $currentOffset; ts_utc = (Get-Date).ToUniversalTime().ToString("o") }
                    continue
                }

                $sub = Resolve-Submolt $intent
                if (-not $sub) { 
                    Block-And-Rollback -reason "BLOCKED_TARGET" -msg "Invalid Target" -fx $fx
                    Write-AtomicJson -Path $CursorFile -Data @{ byte_offset = $currentOffset; ts_utc = (Get-Date).ToUniversalTime().ToString("o") }
                    continue 
                }

                $Mode = Get-SafeJson -Path (Join-Path $RuntimeDir "system_mode.json")
                if ($null -eq $Mode) { $Mode = @{ mode = "OBSERVATION_ONLY" } }

                if ($Mode.mode -like "ACTIVE_*") {
                    $state.inflight | Add-Member -MemberType NoteProperty -Name $id -Value @{ triggered_ts = (Get-Date).ToUniversalTime().ToString("o"); corr_id = $cid; identity = $fx.identity; op = $fx.op_key; spend_txn_id = $fx.spend_txn_id; pid = $PID } -Force
                    Write-Host "T08: Actuating $id (Corr: $cid)" -ForegroundColor Gray
                    Save-State $state
                    
                    if ($DryRun) { Write-Host "[DryRun] Actuating task $sub"; }
                    else {
                        $success = $false
                        $intentType = if ($intent.type) { $intent.type } else { $intent.payload.type }

                        if ($intentType -eq "kill_test") {
                            $Dispatcher = "D:\Infinite\Infinity\Runtime\Decision\Handlers\Axis_Handler_Dispatch.ps1"
                            $res = & $Dispatcher -Intent $intent -SystemMode $Mode.mode
                            if ($res.status -eq "OK") { $success = $true }
                        }
                        else {
                            # Default Moltbook POST
                            & $Client -Action POST -Submolt $sub -Title $intent.payload.title -Content (Get-Content $intent.payload.content_path -Raw) -CorrelationId $cid -Quiet
                            $success = $true
                        }

                        if ($success) {
                            $state.executed_intents += $id
                            if ($state.inflight.PSObject.Properties[$id]) { Remove-Member -InputObject $state.inflight -Name $id -ErrorAction SilentlyContinue }
                            Commit-Spend -iid $id -cid $cid -ident $fx.identity -aeid "SUCCESS" -op $fx.op_key -stxn $fx.spend_txn_id
                            & "D:\Infinite\Infinity\Truth_Engine\T19_ReceiptLedger.ps1" -Action WRITE_RECEIPT -CorrId $cid -OpType $intentType -Target $sub -ReceiptData @{ status = "success"; pid = $PID }
                            $Global:CycleStats.actuations++
                        }
                    }
                }
                else {
                    Append-DecLog "Observer Mode Gating" $id "GATED_OBSERVER" $cid
                }
                
                # COMMIT AT END OF SUCCESSFUL INTENT
                Write-AtomicJson -Path $CursorFile -Data @{ byte_offset = $currentOffset; ts_utc = (Get-Date).ToUniversalTime().ToString("o") }
            }
            $reader.Dispose(); $fs.Dispose()
        }
    }
    catch {
        Write-Error "T08 Cycle Fatal: $_"
        $Global:LastError = $_
    }
    
    # EMIT TELEMETRY STATE
    try {
        $pending = 0
        if (Test-Path $QueueFile) {
            $cursorData = Get-SafeJson -Path $CursorFile
            $offset = if ($cursorData -and $cursorData.byte_offset) { $cursorData.byte_offset } else { 0 }
            $fs2 = [System.IO.File]::Open($QueueFile, "Open", "Read", "ReadWrite")
            $fs2.Seek($offset, "Begin") | Out-Null
            $r2 = New-Object System.IO.StreamReader($fs2, [System.Text.Encoding]::UTF8)
            while (-not $r2.EndOfStream) { if (-not [string]::IsNullOrWhiteSpace($r2.ReadLine())) { $pending++ } }
            $r2.Dispose(); $fs2.Dispose()
        }
        
        $stateOut = @{
            pending_intents       = $pending
            last_processed_corr   = $cid
            last_run_utc          = (Get-Date).ToUniversalTime().ToString("o") + "Z"
            error_count_last_hour = if ($Global:LastError) { 1 } else { 0 }
        }
        $dir = [System.IO.Path]::GetDirectoryName($LocalStateFile)
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        Write-AtomicJson -Path $LocalStateFile -Data $stateOut

        # WRITE FAULT LEDGER
        $ledgerFile = Join-Path $dir "executor_fault_ledger.jsonl"
        $isFault = if ($Global:LastError) { $true } else { $false }
        $errMsg = if ($Global:LastError) { $Global:LastError.ToString() } else { $null }
        
        $ledgerRecord = @{
            timestamp_utc = (Get-Date).ToUniversalTime().ToString("o") + "Z"
            task = "Axis_T08_Pulse_Heartbeat"
            dry_run = $DryRun.IsPresent
            success = (-not $isFault)
            fault = $isFault
            error = $errMsg
            pending_intents = if ($isFault) { $null } else { $pending }
            last_processed_corr = $cid
        }
        
        $jsonStr = $ledgerRecord | ConvertTo-Json -Compress
        Add-Content -Path $ledgerFile -Value $jsonStr -Encoding UTF8
    }
    catch {
        Write-Warning "Failed to emit executor telemetry: $_"
    }
} # End Invoke-WithMutex ScriptBlock

if (-not $t08Lock.lock_acquired) {
    Write-Warning "T08: Mutex timed out. Cycle skipped."
    exit 1
}
