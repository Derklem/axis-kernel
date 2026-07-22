$Root = "D:\Infinite\Infinity"
$SnapFile = Join-Path $Root "Snapshots\2026-02-14\snapshot.json"
$snap = Get-Content $SnapFile -Raw | ConvertFrom-Json
$m = $snap.system_metrics

function Get-Hash {
    param($n, $p)
    $d = Split-Path $p -Parent
    $aDir = Join-Path $d "Archive"
    $segs = @()
    if (Test-Path $aDir) {
        $segs += Get-ChildItem -Path $aDir -Filter "$n.*.jsonl" | Sort-Object Name | ForEach-Object { $_.FullName }
    }
    if (Test-Path $p) { $segs += $p }
    
    for ($i = $segs.Count - 1; $i -ge 0; $i--) {
        if (-not (Test-Path $segs[$i])) { continue }
        $tail = Get-Content $segs[$i] -Tail 5
        $last = $tail | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 1
        if ($last) {
            $obj = $last | ConvertFrom-Json
            if ($obj.hash) { return $obj.hash }
        }
    }
    return "null" # Unified null constant
}

function Get-FileHash {
    param($path)
    if (-not (Test-Path $path)) { return "null" }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $stream = [System.IO.File]::OpenRead($path)
    $hash = [BitConverter]::ToString($sha.ComputeHash($stream)) -replace "-", ""
    $stream.Close()
    return "sha256:" + $hash.ToLower()
}

$keys = @("audit", "spend", "revocation", "policy", "identity", "keyring")
$paths = @{
    "audit"      = "Truth_Engine\audit_trail.jsonl"
    "spend"      = "Truth_Engine\spend_ledger.jsonl"
    "revocation" = "Governance\revocation_ledger.jsonl"
    "policy"     = "Governance\policy_update_ledger.jsonl"
    "identity"   = "Truth_Engine\identity_registry.json"
    "keyring"    = "Truth_Engine\keyring.json"
}
$names = @{
    "audit"      = "audit_trail"
    "spend"      = "spend_ledger"
    "revocation" = "revocation_ledger"
    "policy"     = "policy_update_ledger"
}

$results = @()
$results += "--- HASH COMPARISON ---"
foreach ($k in $keys) {
    if ($k -in @("identity", "keyring")) {
        $computed = Get-FileHash (Join-Path $Root $paths[$k])
    }
    else {
        $computed = Get-Hash $names[$k] (Join-Path $Root $paths[$k])
    }
    $expected = $m.$k.hash
    if ($computed -eq $expected) {
        $results += "PASS: $k ($computed)"
    }
    else {
        $results += "FAIL: $k"
        $results += "  EXP: $expected"
        $results += "  GOT: $computed"
    }
}

$results | Out-File (Join-Path $Root "Governance\mismatch.log") -Encoding UTF8
$results
