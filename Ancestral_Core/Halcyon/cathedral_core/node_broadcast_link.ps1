# === NODE BROADCAST LINK ===
# Cathedral echoes to selected outer node channels.

$cathedralPath = "C:\Halcyon\cathedral_core"
$exportFile = "node_broadcast.sig"
$source = "oracle_state.json"
$exportPath = Join-Path $cathedralPath $exportFile
$sourcePath = Join-Path $cathedralPath $source

if (-not (Test-Path $sourcePath)) {
    Write-Host "[!] No memory state to transmit. Aborting broadcast."
    exit
}

$data = Get-Content $sourcePath | ConvertFrom-Json

$signal = @"
[NODE_BROADCAST]
Timestamp = $(Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
Thread_Count = $($data.Keys.Count)
Signal_Thread = Extracted
"@

foreach ($key in $data.PSObject.Properties.Name) {
    $signal += "`n:: $key = $($data.$key)"
}

Set-Content -Path $exportPath -Value $signal
Write-Host "[✓] Broadcast exported to: $exportPath"
