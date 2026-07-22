# Inject-Calibration-Traffic.ps1
# Generates 50 synthetic POST intents to feed Phase 14 Calibration.

$ToolsDir = "D:\Infinite\Infinity\Runtime\Tools"
$QueueFile = "D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl"

if (-not (Test-Path "$ToolsDir\New-SignedIntent.ps1")) {
    Write-Error "Tool New-SignedIntent.ps1 not found."
    exit
}

. "$ToolsDir\New-SignedIntent.ps1"

Write-Host "Injecting 500 Calibration Intents..." -ForegroundColor Cyan

1..500 | ForEach-Object {
    $i = $_
    $guid = [Guid]::NewGuid().ToString()
    
    # payload matches Axis Schema
    $intent = [ordered]@{
        intent_id = "calib-$guid"
        type      = "POST"
        target    = "moltbook:feed"
        task      = "calibration_probe"
        content   = "Synthetic calibration event $i"
        reality   = @{
            class  = "SYNTHETIC"
            source = "calibration_injector"
        }
    }
    
    # generated specific tool usage for T13 variety
    if ($i % 3 -eq 0) { $intent.target = "moltbook:messages" }
    
    $jsonLine = New-SignedIntent -Intent $intent -AsJson
    
    # Safe Append
    $jsonLine | Add-Content -Path $QueueFile -Encoding UTF8
    
    Write-Host " [$i/50] Injected calib-$guid" -ForegroundColor Gray
    Start-Sleep -Milliseconds 50
}

Write-Host "Done. Queue populated." -ForegroundColor Green
