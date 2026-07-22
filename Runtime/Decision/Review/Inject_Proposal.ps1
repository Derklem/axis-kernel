$Queue = "D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl"
$Outbox = "D:\Infinite\Infinity\Runtime\Decision\Voice\voice_proposals.jsonl"

$line = Get-Content $Outbox -Tail 1
if (-not $line) { throw "Outbox empty" }

$len1 = (Get-Item $Queue).Length
[System.IO.File]::AppendAllText($Queue, $line + "`n", [System.Text.Encoding]::UTF8)
$len2 = (Get-Item $Queue).Length

Write-Host "Initial Len: $len1"
Write-Host "Final Len: $len2"
if ($len2 -gt $len1) { Write-Host "SUCCESS: Appended to queue." }
else { Write-Host "FAILED: Queue did not grow." }
