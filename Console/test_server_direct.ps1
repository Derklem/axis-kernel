$ErrorActionPreference = "Continue"
Write-Host "Testing Minimal Server Direct..."
try {
    $listener = New-Object System.Net.HttpListener
    $listener.Prefixes.Add("http://127.0.0.1:8799/")
    $listener.Start()
    Write-Host "Listening on 8799..."
    
    # Self-test
    $req = [System.Net.WebRequest]::Create("http://127.0.0.1:8799/")
    $req.Method = "GET"
    $req.Timeout = 2000
    $resp = $req.GetResponse()
    Write-Host "Response: $($resp.StatusCode)"
    $resp.Close()
    
    $listener.Stop()
    Write-Host "Stopped."
} catch {
    Write-Host "ERROR: $_"
}
