. "D:\Infinite\Infinity\Runtime\Tools\New-SignedIntent.ps1"

$intent = @{
    intent_id = "INT-TEST-SIGNED-HAPPY"
    domain    = "test"
    target    = "debug"
    task      = "happy_path_verify"
}
$jsonLine = New-SignedIntent -Intent $intent -AsJson
Add-Content -Path "D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl" -Value $jsonLine -Encoding UTF8
Write-Host "Injected signed intent: INT-TEST-SIGNED-HAPPY"
