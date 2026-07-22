# === Bloom Feast Map ===
param(
  [string[]] $Drives   = @('C','D','E','F','G','H','I'),
  [string[]] $Patterns = @('feast','bloom','axis'),
  [switch]   $DoHash
)

$ts       = (Get-Date).ToString('yyyyMMdd_HHmmss')
$outRoot  = 'C:\Lattice_Task_Exports\Feast_Map'
$outDir   = Join-Path $outRoot ("FeastMap_{0}" -f $ts)
$csvPath  = Join-Path $outDir 'feast_map.csv'
$jsonPath = Join-Path $outDir 'feast_map.json'
$sumPath  = Join-Path $outDir 'feast_map_summary.txt'

New-Item -ItemType Directory -Path $outDir -Force | Out-Null

# Build case-insensitive regex once
$rx = ($Patterns | ForEach-Object { [Regex]::Escape($_) }) -join '|'
$rx = "(?i)$rx"

$results = New-Object System.Collections.Generic.List[Object]

foreach ($d in $Drives) {
  $root = "$d`:\"
  if (-not (Test-Path -LiteralPath $root)) { continue }

  $vol = ''
  try { $vol = (Get-Volume -DriveLetter $d -ErrorAction Stop).FileSystemLabel } catch {}

  Write-Host ("Scanning {0} ..." -f $root) -ForegroundColor Cyan

  # Directories with matching names
  Get-ChildItem -LiteralPath $root -Recurse -Directory -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match $rx } |
    ForEach-Object {
      $dir = $_
      $results.Add([PSCustomObject]@{
        Type        = 'Directory'
        Name        = $dir.Name
        FullPath    = $dir.FullName
        SizeBytes   = $null
        LastWriteUTC= $dir.LastWriteTimeUtc
        CreatedUTC  = $dir.CreationTimeUtc
        Attributes  = $dir.Attributes
        Drive       = $d
        VolumeLabel = $vol
        MatchFrom   = 'Name'
        PatternRx   = $rx
        SHA256      = $null
      })
    }

  # Files with matching names
  Get-ChildItem -LiteralPath $root -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match $rx } |
    ForEach-Object {
      $f = $_
      $hash = $null
      if ($DoHash) {
        try { $hash = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256 -ErrorAction Stop).Hash } catch {}
      }
      $results.Add([PSCustomObject]@{
        Type        = 'File'
        Name        = $f.Name
        FullPath    = $f.FullName
        SizeBytes   = $f.Length
        LastWriteUTC= $f.LastWriteTimeUtc
        CreatedUTC  = $f.CreationTimeUtc
        Attributes  = $f.Attributes
        Drive       = $d
        VolumeLabel = $vol
        MatchFrom   = 'Name'
        PatternRx   = $rx
        SHA256      = $hash
      })
    }
}

# Write outputs
$results | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
$results | ConvertTo-Json -Depth 4 | Out-File -Encoding UTF8 $jsonPath

# Summary
$summary = @()
$summary += ("Bloom Feast Map - generated {0}" -f ((Get-Date).ToUniversalTime().ToString('u')))
$summary += ("Scanned drives: {0}" -f ($Drives -join ', '))
$summary += ("Patterns: {0}" -f ($Patterns -join ', '))
$summary += ""

$summary += "Counts by drive:"
$results | Group-Object Drive | Sort-Object Name | ForEach-Object {
  $summary += ("  {0}: {1}" -f $_.Name, $_.Count)
}
$summary += ""

foreach ($token in $Patterns) {
  $c = ($results | Where-Object { $_.Name -like ("*{0}*" -f $token) }).Count
  $summary += ("{0,-8}: {1}" -f $token, $c)
}

$summary += ""
$summary += "Top 20 paths:"
$results | Select-Object -First 20 -Property Type,FullPath,SizeBytes,LastWriteUTC |
  ForEach-Object {
    $summary += ("  [{0}] {1}" -f $_.Type, $_.FullPath)
  }

$summary | Out-File -Encoding UTF8 $sumPath

Write-Host ""
Write-Host ("CSV : {0}" -f $csvPath)
Write-Host ("JSON: {0}" -f $jsonPath)
Write-Host ("SUM : {0}" -f $sumPath)
