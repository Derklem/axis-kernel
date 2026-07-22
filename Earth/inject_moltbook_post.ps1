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

# 2. Construct Payload (P-0004 Ghost Post)
$intent = clip
$ts = [DateTime]::UtcNow.ToString("yyyyMMdd-HHmmss")
$payload = [ordered]@{
    ver    = "1.0"
    id     = "TEST-MB-GHOST-$ts"
    source = $mayaId
    target = "moltbook.post"
    args   = [ordered]@{
        Content     = "Initial Ghost Post via P-0004 Adapter. Safe. Local. Simulated."
        Sustainment = @{
            cigarettes = 92
            soda       = 100
            time       = "SIMULATION"
        }
        Author      = "Axis (Ghost)"
    }
    nonce  = [Guid]::NewGuid().ToString()
    ts_utc = [DateTime]::UtcNow.ToString("o")
}

# 3. Sign
$jsonPayload = $payload | ConvertTo-Json -Depth 5 -Compress
$sig = Compute-HmacSha256Hex -key $secret -message $jsonPayload

# 4. Wrap
$envelope = [ordered]@{
    payload  = $payload
    sig      = $sig
    hash_alg = "HMACSHA256"
}

# 5. Inject to Queue (Robust)
$queuePath = "D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl"
try {
    [System.IO.File]::AppendAllText($queuePath, $envJson + [Environment]::NewLine)
    Write-Host "Injected Ghost Post Intent to: $queuePath"
}
catch {
    Write-Error "Failed to append to queue: $_"
    exit 1
}

# 6. Trigger Execution (Manual Run of T08 to process queue)
Write-Host "Triggering T08 Execution..."
& "D:\Infinite\Infinity\Runtime\Decision\Run_T08.ps1"

# 7. Verify Output
Start-Sleep -Seconds 2
$outbox = "D:\Infinite\Moltbook_Outbox"
$files = Get-ChildItem -Path $outbox -Filter "*.json"
if ($files) {
    Write-Host "SUCCESS: Found $($files.Count) file(s) in Outbox."
    $files | Select-Object Name, LastWriteTime | Format-Table
}
else {
    Write-Warning "FAILURE: No files found in Outbox."
}
