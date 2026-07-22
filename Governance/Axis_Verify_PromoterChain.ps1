# Axis_Verify_PromoterChain.ps1
# Phase 27: Verifier for Promoter output chain
# Verifies:
#  1) promoted_queue items conform to schema and contain deterministic sort keys + sha binding
#  2) output ordering is correct (expires asc, priority desc, ts asc, nonce asc)
#  3) each promoted item has a matching archive record (execution/archive awareness evidence)
#
# Exits non-zero on failure.

param(
    [ValidateSet("intent_queue", "sandbox_queue")]
    [string]$QueueName = "intent_queue"
)

$ErrorActionPreference = "Stop"

$Root = "D:\Infinite\Infinity"
$RuntimeDir = Join-Path $Root "Runtime\Decision"

$PromotedQueueFile = if ($QueueName -eq "sandbox_queue") {
    Join-Path $RuntimeDir "promoted_sandbox_queue.jsonl"
}
else {
    Join-Path $RuntimeDir "promoted_queue.jsonl"
}

$ArchiveFile = Join-Path $RuntimeDir "promoter_archive.jsonl"

function Fail($msg) {
    Write-Host ("[FAIL] " + $msg) -ForegroundColor Red
    exit 1
}

function Parse-IsoUtcOrMax([string]$s) {
    if ([string]::IsNullOrWhiteSpace($s)) { return [DateTime]::MaxValue }
    try { return [DateTimeOffset]::Parse($s).ToUniversalTime().UtcDateTime } catch { return [DateTime]::MaxValue }
}

if (-not (Test-Path $PromotedQueueFile)) { Fail "Missing promoted queue file: $PromotedQueueFile" }
if (-not (Test-Path $ArchiveFile)) { Fail "Missing promoter archive file: $ArchiveFile" }

# Load archive into a hashtable of (nonce|line_sha)
$archiveSet = @{}
foreach ($line in (Get-Content $ArchiveFile -Encoding UTF8)) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
        $evt = $line | ConvertFrom-Json
        if ($evt.event_type -eq "promoter_promoted" -and $evt.nonce -and $evt.line_sha256) {
            $archiveSet[([string]$evt.nonce + "|" + [string]$evt.line_sha256)] = $true
        }
    }
    catch {}
}

$items = @()
$lineNo = 0
foreach ($line in (Get-Content $PromotedQueueFile -Encoding UTF8)) {
    $lineNo++
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
        $obj = $line | ConvertFrom-Json
    }
    catch {
        Fail "Promoted queue JSON parse error at line $lineNo"
    }

    if ($obj.schema -ne "axis.promoted_envelope.v0.1") { Fail "Bad schema at line $lineNo: $($obj.schema)" }
    if (-not $obj.nonce) { Fail "Missing nonce at line $lineNo" }
    if (-not $obj.source_line_sha256) { Fail "Missing source_line_sha256 at line $lineNo" }
    if (-not $obj.envelope) { Fail "Missing envelope at line $lineNo" }
    if (-not $obj.sort_keys) { Fail "Missing sort_keys at line $lineNo" }

    # Archive evidence
    $key = ([string]$obj.nonce + "|" + [string]$obj.source_line_sha256)
    if (-not $archiveSet.ContainsKey($key)) {
        Fail "No matching archive record for nonce=$($obj.nonce) sha=$($obj.source_line_sha256) (line $lineNo)"
    }

    $items += [pscustomobject]@{
        nonce    = [string]$obj.sort_keys.nonce
        priority = [int]($obj.sort_keys.priority)
        expires  = Parse-IsoUtcOrMax ([string]$obj.sort_keys.expires_utc)
        ts       = Parse-IsoUtcOrMax ([string]$obj.sort_keys.ts_utc)
        raw      = $obj
        line_no  = $lineNo
    }
}

# Verify ordering
for ($i = 1; $i -lt $items.Count; $i++) {
    $a = $items[$i - 1]
    $b = $items[$i]

    $ok = $true

    if ($a.expires -gt $b.expires) { $ok = $false }
    elseif ($a.expires -eq $b.expires) {
        if ($a.priority -lt $b.priority) { $ok = $false }
        elseif ($a.priority -eq $b.priority) {
            if ($a.ts -gt $b.ts) { $ok = $false }
            elseif ($a.ts -eq $b.ts) {
                if ($a.nonce -gt $b.nonce) { $ok = $false }
            }
        }
    }

    if (-not $ok) {
        Fail ("Ordering violation between promoted lines {0} and {1}. A(nonce={2}, exp={3}, pri={4}, ts={5})  B(nonce={6}, exp={7}, pri={8}, ts={9})" -f `
                $a.line_no, $b.line_no, $a.nonce, $a.expires.ToString("o"), $a.priority, $a.ts.ToString("o"), `
                $b.nonce, $b.expires.ToString("o"), $b.priority, $b.ts.ToString("o"))
    }
}

Write-Host ("[PASS] Promoter chain verified. items={0} queue={1}" -f $items.Count, $QueueName) -ForegroundColor Green
exit 0
