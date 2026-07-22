# Experience/Start-ExperienceServer.ps1
# Phase 61: Sovereign Experience Layer (UX)
# Serves the "Cockpit" UI on Port 8090.
# This server is NOT the kernel. It is a read-only client host.

param([int]$Port = 8090)

$ErrorActionPreference = "Stop"
$Root = "D:\Infinite\Infinity\Experience"
$PublicDir = Join-Path $Root "public"

Write-Host "--- AXIS EXPERIENCE LAYER (COCKPIT) ---" -ForegroundColor Magenta
Write-Host "Mode: SOVEREIGN CLIENT" -ForegroundColor Gray
Write-Host "Kernel Target: http://localhost:8798" -ForegroundColor Gray

$listener = [System.Net.HttpListener]::new()
# Use localhost instead of 127.0.0.1 to match browser intent better, or handle both.
# If running as Admin, "+" works best, but localhost is safer for non-admin dev.
$listener.Prefixes.Add("http://localhost:$Port/")
$listener.Start()

Write-Host "Listening on http://localhost:$Port/" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray

try {
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response
        $path = $request.Url.LocalPath
        
        # Default to index.html
        if ($path -eq "/") { $path = "/index.html" }
        
        $filePath = Join-Path $PublicDir $path.TrimStart("/")
        
        if (Test-Path $filePath -PathType Leaf) {
            $content = [System.IO.File]::ReadAllBytes($filePath)
            $response.ContentLength64 = $content.Length
            
            switch ([System.IO.Path]::GetExtension($filePath)) {
                ".html" { $response.ContentType = "text/html" }
                ".js"   { $response.ContentType = "application/javascript" }
                ".css"  { $response.ContentType = "text/css" }
                ".png"  { $response.ContentType = "image/png" }
                default { $response.ContentType = "application/octet-stream" }
            }
            
            $response.OutputStream.Write($content, 0, $content.Length)
            $response.Close()
            Write-Host "200 $path" -ForegroundColor Green
        } else {
            $response.StatusCode = 404
            $response.Close()
            Write-Host "404 $path" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "Server Stopped: $_" -ForegroundColor Yellow
} finally {
    if ($listener.IsListening) { $listener.Stop() }
}
