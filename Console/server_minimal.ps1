# server_minimal.ps1
param([int]$Port = 8787)
$ErrorActionPreference = "Continue"
Start-Transcript -Path "D:\Infinite\Infinity\Console\server_transcript_min.log" -Force

Write-Host "Starting Minimal Server on Port $Port..."

$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://127.0.0.1:$Port/")
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()

Write-Host "Listening..."

while ($listener.IsListening) {
    $context = $listener.GetContext()
    $request = $context.Request
    $response = $context.Response
    
    Write-Host "Request: $($request.Url)"
    
    $response.StatusCode = 200
    $buffer = [System.Text.Encoding]::UTF8.GetBytes("OK")
    $response.ContentLength64 = $buffer.Length
    $response.OutputStream.Write($buffer, 0, $buffer.Length)
    $response.OutputStream.Close()
}
