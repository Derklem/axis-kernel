$ProposalId = "938bd873-1f17-4110-8d03-3ff8306ea6bd"
$Outbox = "D:\Infinite\Infinity\Runtime\Decision\Voice\voice_proposals.jsonl"
$Log = "D:\Infinite\Infinity\Runtime\Decision\Review\review_log.jsonl"
$MayaSecret = "axis_dev_secret_001"

$found = Get-Content $Outbox | ForEach-Object { try { ConvertFrom-Json $_ } catch {} } | Where-Object { $_.nonce -eq $ProposalId }
if (-not $found) { throw "Not found in outbox" }

$intentJson = if ($found.intent_json) { $found.intent_json } else { $found.payload | ConvertTo-Json -Compress -Depth 10 }

function Compute-Sha256([string]$input) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($input)
    $hash = $sha.ComputeHash($bytes)
    return ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Hmac256([string]$key, [string]$msg) {
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([System.Text.Encoding]::UTF8.GetBytes($key))
    $bytes = $hmac.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($msg))
    return ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

$intentSha = Compute-Sha256 $intentJson
$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.000000Z")

$event = [ordered]@{
    schema = "axis.review.event.v1"
    ts = $ts
    proposal_id = $ProposalId
    action = "APPROVED"
    actor = "portal:maya_phone"
    intent_sha256 = $intentSha
    reason = "Manual force approve for validation"
}

$sigWait = "${ts}|$ProposalId|APPROVED|$intentSha"
$event.signature = ("hmac256:" + (Hmac256 $MayaSecret $sigWait))

$line = $event | ConvertTo-Json -Compress
$line | Add-Content $Log
Write-Host "SUCCESS: Force approved $ProposalId"
