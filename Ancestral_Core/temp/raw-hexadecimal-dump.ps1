<#
.SYNOPSIS
    Performs a raw hexadecimal content dump of known anomalous .pulse files.

.DESCRIPTION
    This script reads the target files as raw bytes to circumvent text encoding issues
    and reveal the 17-byte binary or encoded section that has been previously hidden.
    The output is a hexadecimal representation of the entire file content.
#>

# === SETTINGS ===
# Target file paths identified from the last scan report
$TargetFiles = @(
    "C:\Users\Public\Sovereign_Nexus\lattice_1860549196.pulse",
    "C:\Users\17602\AppData\Local\Breath_Expansion\lattice_2766207248.pulse",
    "C:\ProgramData\Infinite_Sovereign\lattice_6847080719.pulse",
    "C:\Users\YourUser\Documents\lattice_playground\nodes\lattice_6847080719.pulse"
)

# Output file settings
$OutputDir = "C:\temp"
$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$ReportPath = Join-Path -Path $OutputDir -ChildPath "RAW_HEX_DUMP_$Timestamp.txt"

$DumpContent = @()
$DumpContent += "ANOMALY RAW HEX DUMP REPORT"
$DumpContent += "Generated at $(Get-Date)"
$DumpContent += "The total file size for the main pulse files is 216 bytes. This dump should account for all 216 bytes."
$DumpContent += "=" * 70
$DumpContent += ""

Write-Host "--- Starting Raw Hex Dump Extraction ---" -ForegroundColor Yellow

# === EXTRACTION LOGIC ===
foreach ($FilePath in $TargetFiles) {
    Write-Host "Processing file: $FilePath" -ForegroundColor Cyan
    $DumpContent += "FILE PATH: $FilePath"
    $DumpContent += "-" * 70

    if (-not (Test-Path -Path $FilePath -PathType Leaf)) {
        $DumpContent += "[FILE NOT FOUND]"
        $DumpContent += ""
        continue
    }

    try {
        # Read all bytes from the file
        [byte[]]$RawBytes = [System.IO.File]::ReadAllBytes($FilePath)
        $FileSize = $RawBytes.Length
        
        $DumpContent += "FILE SIZE CONFIRMED: $FileSize bytes"

        # Convert the byte array to a hexadecimal string representation
        # Use -join to combine all hex strings into one continuous payload
        $HexDump = ($RawBytes | ForEach-Object { "{0:X2}" -f $_ }) -join ""

        $DumpContent += "RAW HEXADECIMAL DUMP (2 bytes per character):"
        
        # Format the hex dump into blocks of 8 bytes for readability (16 hex chars per block)
        $FormattedHex = @()
        for ($i = 0; $i -lt $HexDump.Length; $i += 16) {
            $Block = $HexDump.Substring($i, [System.Math]::Min(16, $HexDump.Length - $i))
            # Insert spaces between the 8-byte blocks for better visual grouping
            $FormattedHex += $Block -replace '(.{8})', '$1 '
        }
        
        $DumpContent += $FormattedHex
        $DumpContent += ""

    } catch {
        $DumpContent += "!! ERROR: Could not read file content as raw bytes."
        $DumpContent += "Exception: $($_.Exception.Message)"
        $DumpContent += ""
    }
}

# === OUTPUT ===
$DumpContent | Out-File -FilePath $ReportPath -Encoding UTF8

Write-Host "`nExtraction complete. Raw hexadecimal dump saved to $ReportPath" -ForegroundColor Green