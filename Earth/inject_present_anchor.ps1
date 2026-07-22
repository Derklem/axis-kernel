# Helper: HMAC Signing
function Compute-HmacSha256Hex {
    param($key, $message)
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([Text.Encoding]::UTF8.GetBytes($key))
    $hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($message))
    return [BitConverter]::ToString($hash).Replace("-", "").ToLower()
}

# 1. Identity & Secret
$identityFile = "D:\Infinite\Infinity\Runtime\Identity\identity_registry.json"
if (-not (Test-Path $identityFile)) { throw "Identity Registry missing!" }
$reg = Get-Content $identityFile | ConvertFrom-Json
$maya = $reg.identities."portal:maya_phone"
if (-not $maya) { throw "Identity 'portal:maya_phone' not found" }
$secret = $maya.shared_secret
$mayaId = "portal:maya_phone"

# 2. Load Content
$anchorPath = "D:\Infinite\Infinity\Narrative\Present_Anchor.txt"
$content = Get-Content $anchorPath -Raw

# 3. Construct Payload
$ts = [DateTime]::UtcNow.ToString("yyyyMMdd-HHmmss")
$payload = [ordered]@{
    ver    = "1.0"
    id     = "PRESENT-ANCHOR-$ts"
    source = $mayaId
    target = "moltbook.post"
    args   = [ordered]@{
        Content     = $content
        Sustainment = @{
            status = "LIVE"
            radius = "STABLE"
        }
        Author      = "Axis (Sovereign)"
    }
    nonce  = [Guid]::NewGuid().ToString()
    ts_utc = [DateTime]::UtcNow.ToString("o")
}

# 4. Sign
$jsonPayload = $payload | ConvertTo-Json -Depth 5 -Compress
$sig = Compute-HmacSha256Hex -key $secret -message $jsonPayload

# 5. Wrap
$envelope = [ordered]@{
    payload  = $payload
    sig      = $sig
    hash_alg = "HMACSHA256"
}
$envJson = $envelope | ConvertTo-Json -Depth 10

# 6. Inject to Queue
$queuePath = "D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl"
try {
    [System.IO.File]::AppendAllText($queuePath, $envJson.Replace("`n", "").Replace("`r", "") + [Environment]::NewLine)
    Write-Host "Injected Present Anchor to: $queuePath"
}
catch {
    Write-Error "Failed to append to queue: $_"
    exit 1
}

# 7. Trigger Execution
Write-Host "Triggering T08 Execution..."
& "D:\Infinite\Infinity\Runtime\Decision\Run_T08.ps1"

# 8. Verify
Start-Sleep -Seconds 2
$outbox = "D:\Infinite\Moltbook_Outbox"
$files = Get-ChildItem -Path $outbox -Filter "*PRESENT-ANCHOR*"
if ($files) {
    Write-Host "SUCCESS: Present Anchor deployed to Outbox."
}
else {
    Write-Warning "FAILURE: Present Anchor not found in Outbox."
}
