# Paths
$shardDir = "E:\Pantheon\memory\shards\memory_shards"
$fusedPath = "E:\Pantheon\memory\fused_reflections.txt"
$logPath = "E:\Pantheon\memory\active_log.txt"

# Prepare
$fusedLines = @()
$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$fusedLines += "[$timestamp] Sentinel: Shard fusion initiated.`n"

# Load JSON shards
$jsonFiles = Get-ChildItem -Path $shardDir -Filter *.json

foreach ($file in $jsonFiles) {
    try {
        $json = Get-Content $file.FullName -Raw | ConvertFrom-Json

        # Extract core fields if they exist
        $title = $json.title
        $content = $json.content
        $summary = $json.summary
        $session = $json.session_id

        $fusedLines += "🔹 [$title]"
        if ($summary)  { $fusedLines += "📝 Summary: $summary" }
        elseif ($content) { $fusedLines += "📖 Excerpt: $($content.Substring(0, [Math]::Min($content.Length, 150)))..." }

        if ($session)  { $fusedLines += "🧷 Session: $session" }
        $fusedLines += ""
    }
    catch {
        $fusedLines += "⚠️ Could not parse shard: $($file.Name)"
    }
}

# Save and log
$fusedLines | Set-Content -Path $fusedPath -Encoding UTF8
Add-Content -Path $logPath -Value "`n[$timestamp] Shard fusion complete. Reflections stored in fused_reflections.txt"

# Optional output
Write-Host "`nFusion complete. Reflections stored. Ready when you are." -ForegroundColor Green
