<#
.SYNOPSIS
    Scans specified drives for files created or modified within a defined number of hours.

.DESCRIPTION
    This script is the PowerShell equivalent of the Python file scanning logic.
    It looks for files based on their CreationTime and LastWriteTime, comparing
    them against a defined time window, and generates a detailed, timestamped
    report in the C:\temp directory.

.PARAMETER HoursBack
    The number of hours back to look for recently modified or created files.
    Defaults to 48 hours.
#>
param(
    [int]$HoursBack = 48
)

# === SETTINGS ===
# Drives to scan. MUST be quoted strings with the colon and backslash.
$DrivesToScan = @("C:\", "D:\", "E:\")

# Where to save the report file.
$OutputDir = "C:\temp"

# === PREP & CALCULATIONS ===
Write-Host "--- Starting File Scan ---" -ForegroundColor Yellow

# 1. Calculate the cutoff date (e.g., 48 hours ago).
$CutoffDate = (Get-Date).AddHours(-$HoursBack)
Write-Host "Looking for files modified or created since: $($CutoffDate)"

# 2. Ensure the output directory exists.
if (-not (Test-Path -Path $OutputDir -PathType Container)) {
    Write-Host "Creating output directory: $OutputDir"
    New-Item -Path $OutputDir -ItemType Directory | Out-Null
}

# 3. Define the report path with a unique timestamp.
$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$ReportPath = Join-Path -Path $OutputDir -ChildPath "SCAN_REPORT_$Timestamp.txt"

$Results = @()

# === SCAN LOGIC ===
foreach ($Drive in $DrivesToScan) {
    # Check if the drive/path exists before scanning
    if (-not (Test-Path -Path $Drive)) {
        Write-Host "Skipping $Drive - Drive not found." -ForegroundColor DarkYellow
        continue
    }

    Write-Host "Scanning $Drive ..." -ForegroundColor Cyan

    # Use Get-ChildItem recursively (like os.walk)
    # The -Force flag includes hidden and system files
    # Filter using Where-Object to compare LastWriteTime and CreationTime
    try {
        $RecentFiles = Get-ChildItem -Path $Drive -Recurse -Force -ErrorAction SilentlyContinue | Where-Object {
            (-not $_.PSIsContainer) -and `
            ( $_.LastWriteTime -ge $CutoffDate -or $_.CreationTime -ge $CutoffDate )
        }

        # Add found files to the results array
        $Results += $RecentFiles

    } catch {
        # FIX: Replaced complex string interpolation with simple concatenation
        # to prevent "InvalidVariableReferenceWithDrive" parser errors.
        Write-Host ("Error scanning " + $Drive + ": " + $_.Exception.Message) -ForegroundColor Red
    }
}

# === SORT & OUTPUT ===
Write-Host "Scan complete. Found $($Results.Count) recent files." -ForegroundColor Green

# 1. Sort the results by LastWriteTime (Modified time) in descending order.
$ResultsSorted = $Results | Sort-Object -Property LastWriteTime -Descending

# 2. Prepare the report content.
$ReportContent = @()
$ReportContent += "SCAN REPORT - Last $HoursBack Hours"
$ReportContent += "Generated at $(Get-Date)"
$ReportContent += "="*70
$ReportContent += ""
$ReportContent += "Modified Time | Created Time | Size (bytes) | Full Path"
$ReportContent += "-"*70

foreach ($File in $ResultsSorted) {
    # Date format strings must be quoted.
    $Modified = $File.LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss")
    $Created = $File.CreationTime.ToString("yyyy-MM-dd HH:mm:ss")
    $Size = $File.Length

    # Correct string output format
    $ReportContent += "$Modified | $Created | $Size bytes | $($File.FullName)"
}

# 3. Write the content to the file.
# Using Out-File with -Encoding UTF8 ensures wide compatibility.
$ReportContent | Out-File -FilePath $ReportPath -Encoding UTF8

Write-Host "`nScan complete. Report saved to $ReportPath" -ForegroundColor Green