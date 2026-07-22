<#
.SYNOPSIS
  T20_VerifyReceipts.ps1
  Node 2 Verifier: Ensures decision_log, run_log, and receipt ledger form an unbroken chain.

.PARAMETER IntentId
  Optional filter (e.g. INT-node1-socraticprobe-0001)

.PARAMETER SinceTs
  Optional filter (e.g. 2024-01-01T00:00:00Z)

.PARAMETER Strict
  If set, any violation exits with code 2.
#>

param(
    [string]$IntentId = "",
    [string]$SinceTs = "",
    [switch]$Strict
)

$Base = "D:\Infinite\Infinity"
$DecisionLog = Join-Path $Base "Runtime\Decision\decision_log.jsonl"
$RunLog = Join-Path $Base "Runtime\Moltbook\run_log.jsonl"
$Ledger = Join-Path $Base "Runtime\Receipts\Receipt_Ledger.jsonl"

function Read-Jsonl($path) {
    if (-not (Test-Path $path)) { return @() }
    $lines = Get-Content $path -ErrorAction SilentlyContinue
    $out = New-Object System.Collections.Generic.List[object]
    foreach ($l in $lines) {
        if ([string]::IsNullOrWhiteSpace($l)) { continue }
        try { $out.Add(($l | ConvertFrom-Json)) } catch { }
    }
    return $out
}

$dec = Read-Jsonl $DecisionLog
if ($IntentId) { $dec = $dec | Where-Object { $_.intent_id -eq $IntentId } }

if ($SinceTs) {
    $since = [DateTimeOffset]::Parse($SinceTs).ToUniversalTime()
    $dec = $dec | Where-Object {
        try {
            ([DateTimeOffset]::Parse($_.ts).ToUniversalTime() -ge $since)
        }
        catch { $false }
    }
}

$run = Read-Jsonl $RunLog
$led = Read-Jsonl $Ledger

$violations = New-Object System.Collections.Generic.List[string]

# Index receipts by corr_id
$ledgerByCorr = @{}
foreach ($r in $led) {
    if (-not $r.corr_id) { continue }
    if (-not $ledgerByCorr.ContainsKey($r.corr_id)) { $ledgerByCorr[$r.corr_id] = @() }
    $ledgerByCorr[$r.corr_id] += $r
}

# Index runlog by corr_id (best-effort: supports either corr_id field or embedded text)
$runHasHandshake = @{}
foreach ($e in $run) {
    $cid = $null
    if ($e.corr_id) { $cid = $e.corr_id }
    elseif ($e.message -and ($e.message -match "CORR-[a-f0-9]+")) { $cid = $Matches[0] }
    if (-not $cid) { continue }

    if (-not $runHasHandshake.ContainsKey($cid)) { $runHasHandshake[$cid] = $false }
    $etype = ""
    if ($e.event_type) { $etype = [string]$e.event_type }
    if ($etype -match "client_handshake") { $runHasHandshake[$cid] = $true }
    if ($e.message -and ($e.message -match "client_handshake")) { $runHasHandshake[$cid] = $true }
}

# Walk decisions
foreach ($d in $dec) {
    $res = [string]$d.result
    $cid = $d.corr_id
    $iid = $d.intent_id

    if ($res -eq "BLOCKED_AUTH" -and -not $cid) {
        $violations.Add("BLOCKED_AUTH missing corr_id (intent=$iid)")
        continue
    }

    if (($res -eq "TRIGGERED") -or ($res -eq "FULFILLED")) {
        if (-not $cid) {
            $violations.Add("$res missing corr_id (intent=$iid)")
            continue
        }

        if (-not $ledgerByCorr.ContainsKey($cid)) {
            $violations.Add("$res has no ledger entries (corr_id=$cid intent=$iid)")
            continue
        }

        $entries = $ledgerByCorr[$cid]
        $hasAttempt = $false
        $hasConfirmed = $false

        foreach ($x in $entries) {
            if ($x.type -eq "ATTEMPT") { $hasAttempt = $true }
            if ($x.type -eq "RECEIPT" -and $x.receipt -and $x.receipt.status -eq "confirmed") { $hasConfirmed = $true }
        }

        if (-not $hasAttempt) {
            $violations.Add("$res missing ATTEMPT receipt (corr_id=$cid intent=$iid)")
        }

        if ($res -eq "FULFILLED") {
            if (-not $hasConfirmed) {
                $violations.Add("FULFILLED missing CONFIRMED receipt (corr_id=$cid intent=$iid)")
            }

            $handshake = $false
            if ($runHasHandshake.ContainsKey($cid)) { $handshake = [bool]$runHasHandshake[$cid] }
            if (-not $handshake) {
                $violations.Add("FULFILLED missing client_handshake evidence in run_log (corr_id=$cid intent=$iid)")
            }
        }
    }
}

if ($violations.Count -eq 0) {
    Write-Host "T20 OK: Receipt chain verified." -ForegroundColor Green
    exit 0
}

Write-Host "T20 FAIL: Receipt-chain violations:" -ForegroundColor Yellow
$violations | ForEach-Object { Write-Host (" - " + $_) -ForegroundColor Yellow }

if ($Strict) { exit 2 } else { exit 1 }
