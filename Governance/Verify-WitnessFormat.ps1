
$GovDir = "D:\Infinite\Infinity\Governance"
$WitnessFile = Join-Path $GovDir "test_witness.jsonl"

# Mock Data
$events = @(
    @{ ts_utc="2026-01-01T00:00:00Z"; hash="abc"; type="event1" },
    @{ ts_utc="2026-01-01T00:01:00Z"; hash="def"; type="event2" }
)

Write-Host "Generating Test Witness (JSONL)..."
if (Test-Path $WitnessFile) { Remove-Item $WitnessFile }

foreach ($rec in $events) {
    $line = $rec | ConvertTo-Json -Compress -Depth 10
    Add-Content -Path $WitnessFile -Value $line -Encoding UTF8
}

Write-Host "Verifying Format..."
$lines = Get-Content $WitnessFile
if ($lines.Count -ne 2) {
    Write-Error "FAIL: Expected 2 lines, got $($lines.Count). Likely JSON Array format."
    exit 1
}

$first = $lines[0] | ConvertFrom-Json
if ($first.hash -eq "abc") {
    Write-Host "SUCCESS: JSONL format confirmed." -ForegroundColor Green
} else {
    Write-Error "FAIL: Data mismatch."
}
