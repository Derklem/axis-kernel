$ProposalId = "8b60f59f-b86d-48ce-b081-f3d13c84db37"
$Outbox = "D:\Infinite\Infinity\Runtime\Decision\Voice\voice_proposals.jsonl"
$Log = "D:\Infinite\Infinity\Runtime\Decision\Review\review_log.jsonl"
$MayaSecret = "axis_dev_secret_001"

$lines = Get-Content $Outbox
$foundLine = $null
foreach ($l in $lines) {
    if ($l -like "*$ProposalId*") {
        $foundLine = $l
        break
    }
}

if (-not $foundLine) { throw "Nonce not found in file" }

$obj = $foundLine | ConvertFrom-Json
$intentJson = if ($obj.intent_json) { $obj.intent_json } else { $obj.payload | ConvertTo-Json -Compress -Depth 10 }

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
    reason = "Manual validation injection"
}

$sigWait = "${ts}|$ProposalId|APPROVED|$intentSha"
$event.signature = ("hmac256:" + (Hmac256 $MayaSecret $sigWait))

$line = $event | ConvertTo-Json -Compress
Add-Content $Log $line
Write-Host "Approved: $ProposalId"
