try {
    Write-Host "Sending Request to 8091..."
    $r = Invoke-WebRequest "http://localhost:8091/state/transport" -Method Get -Verbose
    Write-Host "SUCCESS: $($r.StatusCode)"
    Write-Host "Content: $($r.Content)"
} catch {
    $res = $_.Exception.Response
    Write-Host "Status: $($res.StatusCode)"
    if ($res.GetResponseStream()) {
        $reader = New-Object System.IO.StreamReader($res.GetResponseStream())
        Write-Host "Body: $($reader.ReadToEnd())"
    } else {
        Write-Host "Error: $($_.Exception.Message)"
    }
}
