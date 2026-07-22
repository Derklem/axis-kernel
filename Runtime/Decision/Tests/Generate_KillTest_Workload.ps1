# Generate_KillTest_Workload.ps1
param([int]$n = 10)

$TargetFile = "D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl"
$Intents = @()

for ($i = 1; $i -le $n; $i++) {
    $cid = "KILLTEST-$(Get-Date -UFormat %H%M%S)-$i"
    $nonce = [Guid]::NewGuid().ToString("N")
    
    $inner = [ordered]@{
        intent_id = "killtest-$i"
        type      = "kill_test"
        target    = "axis:handler"
        payload   = @{
            id         = "killtest-$i"
            type       = "kill_test"
            parameters = @{}
        }
    }
    $innerJson = $inner | ConvertTo-Json -Compress

    $envelope = [ordered]@{
        schema         = "axis.intent_envelope.v1"
        identity       = "portal:voice_local"
        crypto_mode    = "NONE"
        signature      = "bypass_for_kill_test"
        intent_json    = $innerJson
        correlation_id = $cid
    }
    $Intents += $envelope
}

$FsLib = "D:\Infinite\Axis_FS_Lib.ps1"
if (Test-Path $FsLib) { . $FsLib }

if (-not (Test-Path "D:\Infinite\Infinity\Runtime\Decision\Tests\killtest_payload.txt")) {
    "KILL TEST DATA" | Set-Content "D:\Infinite\Infinity\Runtime\Decision\Tests\killtest_payload.txt"
}

foreach ($in in $Intents) {
    if (Get-Command Append-JsonlLine -ErrorAction SilentlyContinue) {
        Append-JsonlLine -Path $TargetFile -Data $in
    }
    else {
        $in | ConvertTo-Json -Compress | Add-Content $TargetFile -Encoding UTF8
    }
}

Write-Host "Generated $n intents in $TargetFile" -ForegroundColor Green
