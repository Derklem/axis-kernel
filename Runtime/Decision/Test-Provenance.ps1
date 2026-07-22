$base = "http://localhost:8091"
$body = @{
    identity = "portal:maya_phone"
    signature = "test_sig_123"
    intent = @{
        type = "POST"
        verb = "request_tool"
        target = "moltbook:introductions"
        payload = @{
            content_path = "D:\Infinite\Constructs\test_payload.txt"
            title = "Provenance Test"
        }
    }
}
$json = $body | ConvertTo-Json -Depth 5
Invoke-RestMethod -Uri "$base/intents" -Method POST -Body $json -ContentType "application/json"
