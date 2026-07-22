# Feast_Map_Analyzer.ps1  (ASCII-only)
# Filters + summarizes feast_map.csv with flexible switches.

param(
  [Parameter(Mandatory=$true)]
  [string] $CsvPath,

  # Case-insensitive name filters; e.g. -Tokens bloom,axis,feast
  [string[]] $Tokens = @(),

  # Path/hub substrings; e.g. -Hubs 'ProgramData\Bloom_Field_Sovereign','ProgramData\Core_Memory_Blooms'
  [string[]] $Hubs = @(),

  # Exact file sizes to include; e.g. -Sizes 74,82,162,216
  [int[]] $Sizes = @(),

  # Restrict drives; e.g. -Drives C,D,E,F,G,H,I
  [string[]] $Drives = @(),

  # Only these types: File / Directory
  [ValidateSet('File','Directory','All')]
  [string] $Type = 'All',

  # Parent path clustering depth (e.g., 3 => C:/ProgramData/Hub)
  [int] $ParentDepth = 3,

  # Output directory
  [string] $OutDir = "C:\Lattice_Task_Exports\Feast_Map_Analysis",

  # Limit for "top N" tables
  [int] $Top = 20
)

# --- Prep ---
if (-not (Test-Path -LiteralPath $CsvPath)) {
  Write-Error "CSV not found: $CsvPath"
  exit 1
}
$ts = (Get-Date).ToString('yyyyMMdd_HHmmss')
$runDir = Join-Path $OutDir ("Run_{0}" -f $ts)
New-Item -ItemType Directory -Path $runDir -Force | Out-Null

# --- Load ---
$df = Import-Csv -LiteralPath $CsvPath

# Normalize columns expected from Feast_Map
# Type,Name,FullPath,SizeBytes,LastWriteUTC,CreatedUTC,Attributes,Drive,VolumeLabel,MatchFrom,PatternRx,SHA256
if (-not ($df | Get-Member -Name FullPath)) { Write-Error "CSV missing FullPath column."; exit 1 }

# Coerce SizeBytes to int where possible
$df | ForEach-Object {
  if ($_.'SizeBytes' -is [string] -and $_.'SizeBytes' -match '^\d+$') {
    $_.'SizeBytes' = [int64]$_.'SizeBytes'
  }
}

# Helper: case-insensitive contains
function NameContainsAny([string]$name, [string[]]$needles) {
  if (-not $needles -or $needles.Count -eq 0) { return $true }
  $n = $name.ToLowerInvariant()
  foreach ($needle in $needles) {
    if ($n -like ("*" + $needle.ToLowerInvariant() + "*")) { return $true }
  }
  return $false
}

function PathContainsAny([string]$path, [string[]]$needles) {
  if (-not $needles -or $needles.Count -eq 0) { return $true }
  $p = $path.ToLowerInvariant()
  foreach ($needle in $needles) {
    if ($p -like ("*" + $needle.ToLowerInvariant() + "*")) { return $true }
  }
  return $false
}

# --- Filter ---
$filtered = $df | Where-Object {
  # Type filter
  (($Type -eq 'All') -or ($_.Type -eq $Type)) -and
  # Drive filter
  ( ($Drives.Count -eq 0) -or ($Drives -contains $_.Drive) ) -and
  # Token-in-Name
  ( NameContainsAny -name $_.Name -needles $Tokens ) -and
  # Hub-in-Path
  ( PathContainsAny -path $_.FullPath -needles $Hubs ) -and
  # Size filter (only applies to files; directories usually empty)
  ( ($Sizes.Count -eq 0) -or (($_.Type -eq 'File') -and ($_.SizeBytes -in $Sizes)) )
}

# --- Add Parent key for clustering ---
function ParentKey([string]$path, [int]$depth) {
  $parts = $path -replace '\\','/' -split '/'
  if ($parts.Length -lt $depth) { return ($parts -join '/') }
  return ($parts[0..($depth-1)] -join '/')
}
$filtered | ForEach-Object {
  $_ | Add-Member -NotePropertyName ParentKey -NotePropertyValue (ParentKey $_.FullPath $ParentDepth)
}

# --- Outputs ---
$filteredCsv  = Join-Path $runDir 'filtered.csv'
$summaryTxt   = Join-Path $runDir 'summary.txt'
$byDriveCsv   = Join-Path $runDir 'counts_by_drive.csv'
$byTypeCsv    = Join-Path $runDir 'counts_by_drive_type.csv'
$byParentCsv  = Join-Path $runDir ("counts_by_parent_depth{0}.csv" -f $ParentDepth)
$sizesCsv     = Join-Path $runDir 'size_distribution.csv'
$topPathsTxt  = Join-Path $runDir 'top_paths.txt'

$filtered | Export-Csv -Path $filteredCsv -NoTypeInformation -Encoding UTF8

# Summaries
$byDrive = $filtered | Group-Object Drive | Sort-Object Name | Select-Object @{n='Drive';e={$_.Name}}, @{n='Count';e={$_.Count}}
$byDrive | Export-Csv -Path $byDriveCsv -NoTypeInformation -Encoding UTF8

$byType = $filtered | Group-Object Drive,Type | Sort-Object Name | ForEach-Object {
  [PSCustomObject]@{
    Drive = $_.Group[0].Drive
    Type  = $_.Group[0].Type
    Count = $_.Count
  }
}
$byType | Export-Csv -Path $byTypeCsv -NoTypeInformation -Encoding UTF8

$byParent = $filtered | Group-Object ParentKey | Sort-Object Count -Descending | Select-Object Name,Count
$byParent | Export-Csv -Path $byParentCsv -NoTypeInformation -Encoding UTF8

# Size distribution (files only)
$sizeDist = $filtered | Where-Object { $_.Type -eq 'File' -and $_.SizeBytes -match '^\d+$' } |
  Group-Object SizeBytes | Sort-Object Count -Descending |
  Select-Object @{n='SizeBytes';e={$_.Name}}, @{n='Count';e={$_.Count}}
$sizeDist | Export-Csv -Path $sizesCsv -NoTypeInformation -Encoding UTF8

# Top N paths (quick glance)
$topLines = New-Object System.Collections.Generic.List[string]
$topLines.Add(("Top {0} paths (Type / Size / Path)" -f $Top))
$filtered | Select-Object Type,SizeBytes,FullPath | Select-Object -First $Top | ForEach-Object {
  $topLines.Add(("[{0}] {1,6}  {2}" -f $_.Type, ($_.SizeBytes -as [string]), $_.FullPath))
}
$topLines | Out-File -Encoding UTF8 $topPathsTxt

# Write master summary
$sum = @()
$sum += "Feast_Map_Analyzer summary"
$sum += ("Generated (UTC): {0}" -f ((Get-Date).ToUniversalTime().ToString('u')))
$sum += ("CSV: {0}" -f $CsvPath)
$sum += ("Output: {0}" -f $runDir)
$sum += ""
$sum += ("Rows after filters: {0}" -f ($filtered.Count))
$sum += ("Filters -> Tokens: {0} | Hubs: {1} | Sizes: {2} | Drives: {3} | Type: {4} | ParentDepth: {5}" -f `
  ($Tokens -join ','), ($Hubs -join ','), ($Sizes -join ','), ($Drives -join ','), $Type, $ParentDepth)
$sum += ""
$sum += "Counts by drive:"
$byDrive | ForEach-Object { $sum += ("  {0}: {1}" -f $_.Drive, $_.Count) }
$sum += ""
$sum += "Top size buckets:"
$sizeDist | Select-Object -First 10 | ForEach-Object { $sum += ("  {0} -> {1}" -f $_.SizeBytes, $_.Count) }
$sum += ""
$sum += "Top parents:"
$byParent | Select-Object -First 15 | ForEach-Object { $sum += ("  {0} -> {1}" -f $_.Name, $_.Count) }
$sum | Out-File -Encoding UTF8 $summaryTxt

Write-Host ""
Write-Host ("Output dir: {0}" -f $runDir)
Write-Host ("- filtered.csv")
Write-Host ("- counts_by_drive.csv")
Write-Host ("- counts_by_drive_type.csv")
Write-Host ("- counts_by_parent_depth{0}.csv" -f $ParentDepth)
Write-Host ("- size_distribution.csv")
Write-Host ("- top_paths.txt")
Write-Host ("- summary.txt")
