# Damage-AuditTrail.ps1
param(
    [string]$SourceLog = "D:\Infinite\Infinity\Truth_Engine\audit_trail.jsonl",
    [string]$TargetLog = "D:\Infinite\Infinity\Truth_Engine\audit_trail_damaged.jsonl"
)

$lines = Get-Content $SourceLog
if ($lines.Count -lt 2) {
    Write-Host "Not enough lines to damage."
    exit 1
}

# Damage the second entry's prev_hash (index 1)
$lines[1] = $lines[1] -replace '"prev_hash":"sha256:[0-9a-f]{64}"', '"prev_hash":"sha256:DAMAGED_PREV_HASH"'

# Also damage the first entry's hash to test multiple failures
#$lines[0] = $lines[0] -replace '\"hash\":\"sha256:[0-9a-f]{64}\"', '\"hash\":\"sha256:DAMAGED_GENESIS_HASH\"'

$lines | Set-Content $TargetLog -Encoding utf8
Write-Host "Created damaged log at $TargetLog"
