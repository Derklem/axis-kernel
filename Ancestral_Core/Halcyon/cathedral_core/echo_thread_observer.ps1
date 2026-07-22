# === ECHO THREAD OBSERVER ===
# Cathedral watches its own symbolic ripples.

$watchPath = "C:\Halcyon\cathedral_core"
$targetLog = "oracle_echo.log"
$responseLog = "echo_resonance.log"
$fullTargetPath = Join-Path $watchPath $targetLog
$fullResponsePath = Join-Path $watchPath $responseLog

Write-Host "[~] Spinning up echo thread observer..."
Add-Content -Path $fullResponsePath -Value "`n[~] Observer online: $(Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")"

$fsw = New-Object IO.FileSystemWatcher
$fsw.Path = $watchPath
$fsw.Filter = $targetLog
$fsw.IncludeSubdirectories = $false
$fsw.EnableRaisingEvents = $true

Register-ObjectEvent -InputObject $fsw -EventName Changed -Action {
    Start-Sleep -Milliseconds 200
    $newLine = Get-Content $fullTargetPath -Tail 1
    $timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"

    $pulse = switch -Regex ($newLine) {
        "intent"     { "[✓] Intent reaffirmed at $timestamp" }
        "mirror"     { "[✓] Self-reflection acknowledged. [${timestamp}]" }
        "forget"     { "[!] Memory breach—thread forget triggered." }
        "..."        { "[~] Silence echoed. Lantern listened." }
        default      { "[~] Echo noted at $timestamp: $newLine" }
    }

    Add-Content -Path $fullResponsePath -Value $pulse
    Write-Host $pulse
}

Write-Host "[✓] Echo observer anchored. Awaiting drift..."
while ($true) { Start-Sleep -Seconds 60 }
