$Root = "D:\Infinite\Infinity"
$TruthDir = Join-Path $Root "Truth_Engine"
$ArchiveDir = Join-Path $TruthDir "Archive"

function Get-Segments($name, $activePath) {
    $segs = @()
    if (Test-Path $ArchiveDir) {
        $segs += Get-ChildItem -Path $ArchiveDir -Filter "$name.*.jsonl" | Sort-Object Name | ForEach-Object { $_.FullName }
    }
    if (Test-Path $activePath) { $segs += $activePath }
    return $segs
}

$ledgers = @{
    "audit" = @{ n = "audit_trail"; p = Join-Path $TruthDir "audit_trail.jsonl" }
    "spend" = @{ n = "spend_ledger"; p = Join-Path $TruthDir "spend_ledger.jsonl" }
}

foreach ($k in $ledgers.Keys) {
    $l = $ledgers[$k]
    $segs = Get-Segments $l.n $l.p
    Write-Output "--- $k ($($l.n)) ---"
    foreach ($s in $segs) {
        $line = Get-Content $s -First 1
        Write-Output "FILE: $s"
        Write-Output "CONTENT: $line"
    }
}
