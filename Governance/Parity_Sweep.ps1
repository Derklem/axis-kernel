$Root = "D:\Infinite\Infinity"
$SnapFile = Join-Path $Root "Snapshots\2026-02-14\snapshot.json"
$snap = Get-Content $SnapFile -Raw | ConvertFrom-Json
$m = $snap.system_metrics

$keys = @("audit", "spend", "revocation", "policy", "identity", "keyring")
$paths = @{
    "audit"      = "Truth_Engine\audit_trail.jsonl"
    "spend"      = "Truth_Engine\spend_ledger.jsonl"
    "revocation" = "Governance\revocation_ledger.jsonl"
    "policy"     = "Governance\policy_update_ledger.jsonl"
    "identity"   = "Truth_Engine\identity_registry.json"
    "keyring"    = "Truth_Engine\keyring.json"
}

foreach ($k in $keys) {
    if ($k -in "identity", "keyring") {
        $p = Join-Path $Root $paths[$k]
        $sha = [System.Security.Cryptography.SHA256]::Create()
        $stream = [System.IO.File]::OpenRead($p)
        $computed = "sha256:" + ([BitConverter]::ToString($sha.ComputeHash($stream)) -replace "-", "").ToLower()
        $stream.Close()
    }
    else {
        # Simplified ledger hash logic for check
        $target = Join-Path $Root $paths[$k]
        $tail = Get-Content $target -Tail 1
        if ([string]::IsNullOrWhiteSpace($tail)) { $computed = "null" }
        else {
            $obj = $tail | ConvertFrom-Json
            $computed = $obj.hash
        }
    }
    $expected = $m.$k.hash
    $match = ("$computed" -eq "$expected")
    Write-Output "PARITY: $k -> Expected: $expected, Computed: $computed, Match: $match"
}
