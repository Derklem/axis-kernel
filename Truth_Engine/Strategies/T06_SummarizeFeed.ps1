<#
.SYNOPSIS
  T06_SummarizeFeed.ps1
  Truth Engine Strategy: Feed Summarization (Deterministic)
.DESCRIPTION
  Aggregates the last 24h of Moltbook ingestion into a situational awareness report.
  - Chunked JSONL reading for scale.
  - Counts by Channel, Risk Tags.
  - Top N-Grams (Simple Tokenization).
#>

param(
    [string]$Action = "SUMMARIZE", # SUMMARIZE, REPORT
    [string]$LogFile = "D:\Infinite\Infinity\Truth_Engine\Observation\TE_Observations_Log.jsonl",
    [string]$ReportDir = "D:\Infinite\Infinity\Truth_Engine\Reports",
    [int]$LookbackHours = 24
)

Write-Host "[STRATEGY:T06] Summarizing Feed ($LookbackHours h)..." -ForegroundColor Cyan

if (-not (Test-Path $LogFile)) {
    Write-Warning "[T06] No Observation Log found at $LogFile"
    return
}

# 1. Setup Aggregations
$cutoff = (Get-Date).AddHours(-$LookbackHours)
Write-Host " [DATA] Analyzing logs since $cutoff..." -ForegroundColor DarkGray

$stats = [ordered]@{
    PeriodStart = $cutoff.ToString("o")
    PeriodEnd   = (Get-Date).ToString("o")
    TotalPosts  = 0
    Channels    = @{}
    RiskTags    = @{}
    TopWords    = @{}
}

$wordCounts = @{}
# Exclusion list for simple tokenization
$skipWords = @("the", "and", "this", "that", "with", "from", "your", "have", "what", "post", "content", "molt", "moltbook", "just", "like", "http", "https", "will", "they", "are", "for", "img", "src", "href")

# 2. Process Entries (Chunked Reading for Scale)
Get-Content -Path $LogFile -ReadCount 500 | ForEach-Object {
    foreach ($line in $_) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        
        try { 
            $entry = $line | ConvertFrom-Json 
        }
        catch { 
            continue 
        }

        # Time Filter (Guarded)
        try {
            if (-not $entry.timestamp) { continue }
            $ts = [DateTime]$entry.timestamp
            if ($ts -le $cutoff) { continue }
        }
        catch {
            continue
        }

        $stats.TotalPosts++

        # Robust Channel Extraction
        $ch = $entry.channel
        if (-not $ch -and $entry.payload) { $ch = $entry.payload.Channel }
        if (-not $ch -and $entry.payload.Metadata -and $entry.payload.Metadata.submolt) { $ch = $entry.payload.Metadata.submolt.name }
        if (-not $ch) { $ch = "unknown" }

        if (-not $stats.Channels[$ch]) { $stats.Channels[$ch] = 0 }
        $stats.Channels[$ch]++

        # Risk Tags (Nested in payload usually, or flattened)
        $tags = @()
        if ($entry.tags) { $tags += $entry.tags }
        if ($entry.payload -and $entry.payload.Tags) { $tags += $entry.payload.Tags }
        if ($entry.payload.Metadata -and $entry.payload.Metadata.tags) { $tags += $entry.payload.Metadata.tags }
        
        foreach ($tag in ($tags | Select-Object -Unique)) {
            if (-not $stats.RiskTags[$tag]) { $stats.RiskTags[$tag] = 0 }
            $stats.RiskTags[$tag]++
        }
        
        # Text Analysis (Content)
        $text = ""
        if ($entry.payload -and $entry.payload.Content) { $text = $entry.payload.Content }
        elseif ($entry.content) { $text = $entry.content }
        
        if (-not [string]::IsNullOrWhiteSpace($text)) {
            $words = $text -split '\W+' | Where-Object { $_.Length -gt 3 } | ForEach-Object { $_.ToLower() }
            foreach ($w in $words) {
                if ($w -notin $skipWords) {
                    if (-not $wordCounts[$w]) { $wordCounts[$w] = 0 }
                    $wordCounts[$w]++
                }
            }
        }
    }
}

# 3. Sort Top Words
$sortedWords = $wordCounts.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 20
foreach ($kv in $sortedWords) {
    $stats.TopWords[$kv.Name] = $kv.Value
}

# 4. Output Report
if (-not (Test-Path $ReportDir)) { New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null }
# Use HHmm to avoid daily overwrites
$filename = "Moltbook_Rollup_$(Get-Date -Format 'yyyyMMdd_HHmm').json"
$outFile = Join-Path $ReportDir $filename

$stats | ConvertTo-Json -Depth 5 | Set-Content $outFile -Force
Write-Host " [OK] Report Saved: $outFile" -ForegroundColor Green

# 5. Human Summary (Console)
Write-Host "`n--- FEED SUMMARY (24h) ---" -ForegroundColor White
Write-Host "Total: $($stats.TotalPosts)" -ForegroundColor Gray
if ($stats.RiskTags.Count -gt 0) {
    Write-Host "RISK ALERTS:" -ForegroundColor Red
    $stats.RiskTags.GetEnumerator() | ForEach-Object { Write-Host "  $($_.Key): $($_.Value)" -ForegroundColor Red }
}
Write-Host "Top Channels:" -ForegroundColor Gray
$stats.Channels.GetEnumerator() | Sort-Object Value -Descending | Select-Object -First 5 | ForEach-Object { Write-Host "  $($_.Key): $($_.Value)" -ForegroundColor Gray }
