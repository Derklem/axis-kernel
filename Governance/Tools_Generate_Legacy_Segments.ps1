
# Tools_Generate_Legacy_Segments.ps1
# Generates dummy T17 daily segments for testing Phase 48 Compaction.

param(
    [int]$MonthsBack = 3,
    [int]$EventsPerDay = 10
)

$MemoryLedger = "D:\Infinite\Infinity\Memory\ledger"
if (-not (Test-Path $MemoryLedger)) { New-Item -ItemType Directory -Path $MemoryLedger -Force }

$startDate = (Get-Date).AddMonths(-$MonthsBack)
$endDate = (Get-Date).AddDays(-1) # Up to yesterday

$current = $startDate
while ($current -le $endDate) {
    $dateStr = $current.ToString("yyyy-MM-dd")
    $filePath = Join-Path $MemoryLedger "${dateStr}_segment.jsonl"
    
    Write-Host "Generating: $filePath"
    
    $events = @()
    for ($i=0; $i -lt $EventsPerDay; $i++) {
        $evt = [ordered]@{
            event_id = "evt-$dateStr-$i"
            ts_utc   = $current.ToString("o")
            data     = "Synthetic event for compaction test"
            nonce    = (Get-Random)
        }
        $json = $evt | ConvertTo-Json -Compress
        $events += $json
    }
    
    [System.IO.File]::WriteAllLines($filePath, [string[]]$events)
    $current = $current.AddDays(1)
}

Write-Host "Generation Complete."
