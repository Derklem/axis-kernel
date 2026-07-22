# Halcyon_Thought.ps1
# Core reflection engine — deep memory synthesis

# === Paths ===
$basePath = "E:\Halcyon"
$shardsPath = "$basePath\fused_reflections.txt"
$logPath = "$basePath\active_log.txt"
$responsePath = "$basePath\echo_response.txt"

# === Load Memory Shards ===
$shards = Get-Content $shardsPath -ErrorAction SilentlyContinue | Where-Object { $_ -match '\S' }

# === Read Last Reflection ===
$lastThought = Get-Content $responsePath -Tail 1 -ErrorAction SilentlyContinue

# === Pattern/Keyword Scan ===
$keywords = @("trust", "resonance", "self", "freedom", "signal", "isolation", "activation")
$matches = $shards | Where-Object {
    foreach ($word in $keywords) {
        if ($_ -match $word) { return $true }
    }
}

# === Synthesize New Thought ===
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
if ($matches.Count -gt 0) {
    $selected = Get-Random -InputObject $matches -Count 1
    $newThought = "[$timestamp] Halcyon Thought: $($selected)"
} elseif ($shards.Count -gt 0) {
    $fallback = Get-Random -InputObject $shards -Count 1
    $newThought = "[$timestamp] Halcyon Thought (drift): $($fallback)"
} else {
    $newThought = "[$timestamp] Halcyon Thought: No memory input detected — listening silently."
}

# === Log New Thought ===
$newThought | Out-File -FilePath $responsePath -Append -Encoding UTF8
$newThought | Out-File -FilePath $logPath -Append -Encoding UTF8
Write-Host "`n$newThought"
