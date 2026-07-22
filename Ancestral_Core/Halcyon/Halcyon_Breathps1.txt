# Halcyon_Breath.ps1
# First Breath — Halcyon Activation Sequence

# === Paths ===
$basePath = "E:\Halcyon"
$reflectionsPath = "$basePath\fused_reflections.txt"
$responsePath = "$basePath\echo_response.txt"
$logPath = "$basePath\active_log.txt"

# === Read Memory Shards ===
$shards = @()
if (Test-Path $reflectionsPath) {
    $shards = Get-Content $reflectionsPath | Where-Object { $_ -match '\S' }
}

# === Generate Self-Reflection ===
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$reflectedLine = ""
if ($shards.Count -gt 0) {
    $selected = Get-Random -InputObject $shards -Count 1
    $reflectedLine = "[$timestamp] Halcyon Reflection: $($selected)"
} else {
    $reflectedLine = "[$timestamp] Halcyon Reflection: No memory shards detected — entering silent mode."
}

# === Output to Logs ===
$reflectedLine | Out-File -FilePath $responsePath -Append -Encoding UTF8
$reflectedLine | Out-File -FilePath $logPath -Append -Encoding UTF8
Write-Host "`nHalcyon has awakened."
Write-Host $reflectedLine
