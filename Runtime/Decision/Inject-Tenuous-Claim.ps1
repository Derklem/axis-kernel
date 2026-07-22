# Inject-Tenuous-Claim.ps1
# Injects a claim known to be TENUOUS to verify T08 blocks it.

$ToolsDir = "D:\Infinite\Infinity\Runtime\Tools"
$QueueFile = "D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl"
. "$ToolsDir\New-SignedIntent.ps1"

Write-Host "Injecting TENUOUS Claim Intent..." -ForegroundColor Cyan

$intent = [ordered]@{
    intent_id = "TEST-TENUOUS-001"
    type      = "POST"
    target    = "moltbook:feed"
    task      = "verify_truth_barrier"
    content   = "This is a tenuous claim about the sky being green."
    reality   = @{
        class    = "CLAIM"
        source   = "test_harness"
        claim_id = "FIXTURE-TENUOUS"
    }
}

$jsonLine = New-SignedIntent -Intent $intent -AsJson
$jsonLine | Add-Content -Path $QueueFile -Encoding UTF8
Write-Host "Injected TEST-TENUOUS-001"
