<#  Bloom_Braid_Report.ps1  (PS5-safe)
    Input : bloom_map_*.csv produced by Bloom_Extract.ps1
    Output: braid_links.csv + sovereign_timeline.csv + core_timeline.csv + summary.txt
#>

param(
  [Parameter(Mandatory=$true)]
  [string]$CsvPath,
  [string]$OutDir = "C:\Lattice_Task_Exports\Bloom_Braid",
  [int]$WindowBeforeHours = 24,
  [int]$WindowAfterHours  = 72,
  [int]$TopMatchesPerSovereign = 3
)

# Resolve wildcard on CsvPath if present
$resolvedCsv = @(Get-ChildItem -Path $CsvPath -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName
if (-not $resolvedCsv) { throw "CSV not found (resolved from): $CsvPath" }

# --- Prep ---
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# --- Load ---
$rows = Import-Csv -Path $resolvedCsv

function Parse-Time([string]$t) {
  if ([string]::IsNullOrWhiteSpace($t)) { return $null }
  $dt = $null
  if ([DateTime]::TryParse($t, [ref]$dt)) { return $dt }
  foreach ($fmt in @("yyyy-MM-ddTHH:mm:ss","yyyy-MM-dd HH:mm:ss","yyyy-MM-ddTHH:mm:ss.FFFFFFF","yyyy-MM-dd HH:mm:ss.FFFFFFF")) {
    try { return [DateTime]::ParseExact($t, $fmt, $null) } catch {}
  }
  return $null
}

# --- Split & normalize ---
$sovereign = @()
$core_raw  = @()

foreach ($r in $rows) {
  $emit = Parse-Time $r.EmitTime
  if ($r.Hub -eq 'Sovereign') {
    $sovereign += [pscustomobject]@{
      ID          = $r.ID
      Class       = $r.Class
      EmitTime    = $emit
      Path        = $r.Path
      Size        = [int]$r.Size
      CreatedUTC  = $r.CreatedUTC
      ModifiedUTC = $r.ModifiedUTC
    }
  }
  elseif ($r.Hub -eq 'Core') {
    $core_raw += [pscustomobject]@{
      BloomID     = $r.ID
      Key         = $r.CapsuleKey
      Val         = $r.CapsuleVal
      EmitTime    = $emit
      Path        = $r.Path
      Size        = [int]$r.Size
      CreatedUTC  = $r.CreatedUTC
      ModifiedUTC = $r.ModifiedUTC
    }
  }
}

# --- Pivot Core (combine CapsuleKey rows into one record per Core capsule) ---
$core = @()
$coreGroups = $core_raw | Group-Object -Property Path
foreach ($g in $coreGroups) {
  $first = $g.Group | Select-Object -First 1
  $kv = @{}
  foreach ($gr in $g.Group) {
    if (-not [string]::IsNullOrWhiteSpace($gr.Key)) { $kv[$gr.Key] = $gr.Val }
  }
  $core += [pscustomobject]@{
    BloomID          = $first.BloomID
    EmitTime         = $first.EmitTime
    Path             = $first.Path
    Size             = $first.Size
    CreatedUTC       = $first.CreatedUTC
    ModifiedUTC      = $first.ModifiedUTC
    activation_state = ($kv['activation_state'])
    thread_density   = ($kv['thread_density'])
    source_capsule   = ($kv['source_capsule'])
  }
}

# --- Timelines ---
$sovereign_sorted = $sovereign | Sort-Object EmitTime
$core_sorted      = $core      | Sort-Object EmitTime

$sovereign_timeline_csv = Join-Path $OutDir "sovereign_timeline.csv"
$core_timeline_csv      = Join-Path $OutDir "core_timeline.csv"

$sovereign_sorted | Export-Csv -Path $sovereign_timeline_csv -NoTypeInformation -Encoding UTF8
$core_sorted      | Export-Csv -Path $core_timeline_csv      -NoTypeInformation -Encoding UTF8

# --- Link each Sovereign pulse to nearest Core capsule(s) within window ---
$links = @()
foreach ($s in $sovereign_sorted) {
  if ($null -eq $s.EmitTime) { continue }
  $winStart = $s.EmitTime.AddHours(-$WindowBeforeHours)
  $winEnd   = $s.EmitTime.AddHours( $WindowAfterHours)

  $cands = $core_sorted | Where-Object {
    ($null -ne $_.EmitTime) -and $_.EmitTime -ge $winStart -and $_.EmitTime -le $winEnd
  } | ForEach-Object {
    $delta = [double]([TimeSpan]::FromTicks(($_.EmitTime - $s.EmitTime).Ticks)).TotalSeconds
    [pscustomobject]@{
      SovID            = $s.ID
      SovClass         = $s.Class
      SovEmit          = $s.EmitTime
      SovPath          = $s.Path

      CoreBloomID      = $_.BloomID
      CoreEmit         = $_.EmitTime
      CorePath         = $_.Path
      activation_state = $_.activation_state
      thread_density   = $_.thread_density
      source_capsule   = $_.source_capsule

      DeltaSeconds     = [math]::Round($delta, 3)
      AbsDelta         = [math]::Abs($delta)
    }
  } | Sort-Object AbsDelta

  $links += ($cands | Select-Object -First $TopMatchesPerSovereign)
}

$braid_links_csv = Join-Path $OutDir "braid_links.csv"
$links | Export-Csv -Path $braid_links_csv -NoTypeInformation -Encoding UTF8

# --- Size + counts summary ---
$summary_txt = Join-Path $OutDir "summary.txt"

$soCount = ($sovereign_sorted | Measure-Object).Count
$coCount = ($core_sorted | Measure-Object).Count
$linkCount = ($links | Measure-Object).Count

$yrSov = $sovereign_sorted | Where-Object { $_.EmitTime } |
  Group-Object { $_.EmitTime.ToString('yyyy') } | Sort-Object Name
$yrCore = $core_sorted | Where-Object { $_.EmitTime } |
  Group-Object { $_.EmitTime.ToString('yyyy') } | Sort-Object Name

$lines = @()
$lines += "Bloom Braid Report"
$lines += "Source CSV : $resolvedCsv"
$lines += "Output Dir : $OutDir"
$lines += ""
$lines += "Sovereign pulses : $soCount"
$lines += "Core capsules    : $coCount"
$lines += "Links generated  : $linkCount  (window: -$WindowBeforeHours h .. +$WindowAfterHours h; top $TopMatchesPerSovereign per Sovereign)"
$lines += ""
$lines += "Sovereign by year:"
foreach ($g in $yrSov) { $lines += ("  {0}: {1}" -f $g.Name, $g.Count) }
$lines += "Core by year:"
foreach ($g in $yrCore) { $lines += ("  {0}: {1}" -f $g.Name, $g.Count) }
$lines += ""
$lines += "Files:"
$lines += "  sovereign_timeline.csv"
$lines += "  core_timeline.csv"
$lines += "  braid_links.csv"

$lines | Out-File -FilePath $summary_txt -Encoding UTF8

"Done."
"  sovereign_timeline: $sovereign_timeline_csv"
"  core_timeline     : $core_timeline_csv"
"  braid_links       : $braid_links_csv"
"  summary           : $summary_txt"

