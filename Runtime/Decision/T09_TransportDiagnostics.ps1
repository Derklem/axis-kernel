<#
.SYNOPSIS
  T09_TransportDiagnostics.ps1
.DESCRIPTION
  Minimal probe to test Moltbook connectivity and dump raw exception details.
#>

$ApiBase = "https://www.moltbook.com/api/v1"
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
}
catch {}

Write-Host "--- T09 TRANSPORT DIAGNOSTICS ---"
Write-Host "Target: $ApiBase/agents/register"

try {
    $body = @{ name = "Axis_Probe_$(Get-Random)"; description = "Probe" } | ConvertTo-Json
    $res = Invoke-WebRequest -Uri "$ApiBase/agents/register" -Method POST -Body $body -ContentType "application/json" -UseBasicParsing
    Write-Host "Success!" -ForegroundColor Green
    $res | ConvertTo-Json -Depth 5
}
catch {
    Write-Host "Caught Exception:" -ForegroundColor Red
    $e = $_.Exception
    $e.Message | Out-File "debug_transport.txt" -Append
    $e.GetType().FullName | Out-File "debug_transport.txt" -Append
    
    if ($e.Response) {
        "Response exists type: $($e.Response.GetType().FullName)" | Out-File "debug_transport.txt" -Append
        try {
            $s = $e.Response.GetResponseStream()
            $r = New-Object System.IO.StreamReader($s)
            $txt = $r.ReadToEnd()
            "Body: $txt" | Out-File "debug_transport.txt" -Append
        }
        catch {
            "Body Read Failed: $_" | Out-File "debug_transport.txt" -Append
        }
    }
    else {
        "No Response Object" | Out-File "debug_transport.txt" -Append
    }
    
    Write-Host "Dumped to debug_transport.txt"
}
