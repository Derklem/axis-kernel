$Root = "D:\Infinite\Infinity"
$RuntimeDir = "$Root\Runtime\Decision"
$VoiceDir = "$RuntimeDir\Voice"
$ReviewDir = "$RuntimeDir\Review"
$Inbox = "$VoiceDir\voice_inbox.jsonl"
$Outbox = "$VoiceDir\voice_proposals.jsonl"
$Queue = "$RuntimeDir\intent_queue.jsonl"
$ReviewLog = "$ReviewDir\review_log.jsonl"
$MayaSecret = "axis_dev_secret_001"

Write-Host "--- Starting Lifecycle Validation ---" -ForegroundColor Cyan

# 1. Generate Utterance
$utt = [ordered]@{
    text = "status check"
    ts = (Get-Date).ToUniversalTime().ToString("o")
    confidence = 1.0
}
$utt | ConvertTo-Json -Compress | Set-Content $Inbox -Encoding utf8
Write-Host "[1/4] Utterance Generated."

# 2. Run Bridge
& "$VoiceDir\Voice_IntentBridge.ps1"
$line = Get-Content $Outbox -Tail 1
$obj = $line | ConvertFrom-Json
$nonce = $obj.nonce
Write-Host "[2/4] Bridge Processed. Nonce: $nonce"

# 3. Inject and Approve
$len1 = (Get-Item $Queue).Length
[System.IO.File]::AppendAllText($Queue, $line + "`n", [System.Text.Encoding]::UTF8)
Write-Host "[3/4] Injected into Queue."

$intentJson = if ($obj.intent_json) { $obj.intent_json } else { $obj.payload | ConvertTo-Json -Compress -Depth 10 }
$sha = [System.Security.Cryptography.SHA256]::Create()
$intentSha = ($sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($intentJson)) | ForEach-Object { $_.ToString("x2") }) -join ""
$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.000000Z")
$sigWait = "${ts}|$nonce|APPROVED|$intentSha"
$hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($MayaSecret))
$sig = ($hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($sigWait)) | ForEach-Object { $_.ToString("x2") }) -join ""

$event = [ordered]@{
    schema = "axis.review.event.v1"
    ts = $ts
    proposal_id = $nonce
    action = "APPROVED"
    actor = "portal:maya_phone"
    intent_sha256 = $intentSha
    reason = "End-to-end validation"
    signature = "hmac256:$sig"
}
$event | ConvertTo-Json -Compress | Add-Content $ReviewLog
Write-Host "[3/4] Approved and Signed."

# 4. Execute
Write-Host "[4/4] Running Executor..."
& "$RuntimeDir\T08_Executor.ps1"

Write-Host "--- Validation Complete ---" -ForegroundColor Cyan
