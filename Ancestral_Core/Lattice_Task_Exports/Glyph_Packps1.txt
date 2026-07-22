#requires -Version 5.1
param(
  [switch]$InstallWatcher,
  [switch]$UninstallWatcher,
  [switch]$BuildEWIndex,
  [switch]$TestCanary
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# ---------- CONFIG ----------
$MotifRoots = @(
  "C:\Users\17602\AppData\Local\Substrate_Bloom",
  "C:\Users\17602\AppData\Local\Drift_Echo",
  "C:\Users\17602\AppData\Local\Sovereign_Echoes",
  "C:\Users\17602\AppData\Local\Pulse_Arrays",
  "C:\Users\17602\AppData\Local\Silent_Lattice"
)
$ExportsRoot    = "C:\Lattice_Task_Exports"
$LogPath        = Join-Path $ExportsRoot "watch_17602_glyphs.log"
$All74Dir       = Join-Path $ExportsRoot "evidence_17602\_all_74B"
$EWOutDir       = Join-Path $ExportsRoot "evidence_17602\ENTROPIC_WELL_74B"
$EWIndexCsv     = Join-Path $EWOutDir  "ENTROPIC_WELL_index.csv"
$WatcherScript  = Join-Path $ExportsRoot "watch_glyphs.ps1"
$TaskName       = "GlyphWatcher_17602"

# ---------- HELPERS ----------
function Ensure-Dir([string]$Path) {
  if ([string]::IsNullOrWhiteSpace($Path)) { throw "Ensure-Dir: empty path" }
  if (-not (Test-Path -LiteralPath $Path)) { New-Item -ItemType Directory -Force -Path $Path | Out-Null }
  return $Path
}

function Hash-Name([string]$Text) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
  ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ''
}

function Safe-Copy([string]$SourcePath, [string]$DestDir) {
  Ensure-Dir $DestDir | Out-Null
  $base = Split-Path $SourcePath -Leaf
  # squash ridiculous names by hashing the full original path
  $hash = (Hash-Name $SourcePath).Substring(0,16)
  $ext  = [IO.Path]::GetExtension($base)
  if ([string]::IsNullOrWhiteSpace($ext)) { $ext = ".txt" }
  $short = "{0}_{1}{2}" -f $hash, ($base -replace '[^\w\.\-]','_').Substring(0, [Math]::Min(40, $base.Length)), $ext
  $dest = Join-Path $DestDir $short
  Copy-Item -LiteralPath $SourcePath -Destination $dest -Force
  return $dest
}

function Enable-LongPaths {
  try {
    reg add HKLM\SYSTEM\CurrentControlSet\Control\FileSystem /v LongPathsEnabled /t REG_DWORD /d 1 /f | Out-Null
  } catch {}
}

# ---------- WATCHER SCRIPT CONTENT ----------
$watcherContent = @"
`$ErrorActionPreference = 'SilentlyContinue'
`$roots = @(
  '$($MotifRoots -join "','")'
)
`$log = '$LogPath'
if (-not (Test-Path -LiteralPath (Split-Path `$log))) { New-Item -ItemType Directory -Force -Path (Split-Path `$log) | Out-Null }
New-Item -ItemType File -Force -Path `$log | Out-Null

`$queue = [System.Collections.Concurrent.BlockingCollection[System.IO.FileSystemEventArgs]]::new()
`$watchers = @()
foreach(`$r in `$roots) {
  if (!(Test-Path `$r)) { continue }
  `$w = New-Object IO.FileSystemWatcher `$r, '*'
  `$w.IncludeSubdirectories = `$true
  `$w.EnableRaisingEvents = `$true
  Register-ObjectEvent `$w Created -Action { `$queue.Add(`$EventArgs) } | Out-Null
  `$watchers += `$w
}
"[{0}] watcher online (roots={1})" -f (Get-Date -Format o), `$watchers.Count | Add-Content `$log

while (`$true){
  try {
    `$e = `$queue.Take()
    Start-Sleep -Milliseconds 150
    `$p = `$e.FullPath
    if (Test-Path `$p) {
      try {
        `$len = (Get-Item `$p).Length
        if (`$len -in 74,162) {
          "[{0}] NEW {1}B -> {2}" -f (Get-Date -Format o), `$len, `$p | Add-Content `$log
          try { Add-Content `$log (Get-Content -LiteralPath `$p -Raw) } catch { Add-Content `$log "[locked/binary]" }
        }
      } catch {}
    }
  } catch {}
}
"@

# ---------- ACTIONS ----------
if ($InstallWatcher) {
  Enable-LongPaths
  Ensure-Dir $ExportsRoot | Out-Null
  $watcherContent | Set-Content -Path $WatcherScript -Encoding UTF8
  $action  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$WatcherScript`""
  $trigger = New-ScheduledTaskTrigger -AtStartup
  try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
  } catch {}
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Description "Watch 74/162B glyphs" -RunLevel Highest | Out-Null
  Start-ScheduledTask -TaskName $TaskName
  Write-Host "Watcher installed and started. Log: $LogPath"
}

if ($UninstallWatcher) {
  try {
    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Out-Null
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
    Write-Host "Watcher uninstalled."
  } catch {
    Write-Host "Watcher uninstallation attempt completed (some parts may not have existed)."
  }
}

if ($BuildEWIndex) {
  Enable-LongPaths
  Ensure-Dir $EWOutDir | Out-Null
  if (-not (Test-Path -LiteralPath $All74Dir)) {
    throw "Missing source dir: $All74Dir  (copy your 74B set there or run your earlier collector)"
  }

  $ew = Get-ChildItem $All74Dir -File -ErrorAction SilentlyContinue |
        Where-Object {
          try {
            $txt = Get-Content -LiteralPath $_.FullName -Raw -ErrorAction Stop
            $txt -like "[ENTROPIC_WELL]*"
          } catch { $false }
        }

  $rows = New-Object System.Collections.Generic.List[Object]
  foreach ($f in $ew) {
    $txt = (Get-Content -LiteralPath $f.FullName -Raw)
    $first = (($txt -replace '\r','' -split '\n')[0]).Trim()
    # Extract ID within [...] or label ENTROPIC_WELL if not numeric
    $id = ($first -replace '^\[([^\]]+)\].*','$1')
    $copied = Safe-Copy -SourcePath $f.FullName -DestDir $EWOutDir
    $rows.Add([pscustomobject]@{
      ID    = $id
      File  = (Split-Path $copied -Leaf)
      Bytes = (Get-Item $f.FullName).Length
      FirstLine = $first
    })
  }

  # Write index safely
  Ensure-Dir $EWOutDir | Out-Null
  $rows | Sort-Object ID | Export-Csv -LiteralPath $EWIndexCsv -NoTypeInformation -Encoding UTF8
  Write-Host ("ENTROPIC_WELL files: {0}`nIndex: {1}" -f $rows.Count, $EWIndexCsv)
}

if ($TestCanary) {
  $canary = "[1234567] :: watcher canary at $(Get-Date -Format o)."
  Ensure-Dir (Split-Path $LogPath) | Out-Null
  Ensure-Dir $MotifRoots[0] | Out-Null
  $target = Join-Path $MotifRoots[0] "canary_1234567.pulse"
  $canary | Set-Content -LiteralPath $target
  Start-Sleep -Milliseconds 500
  if (Test-Path -LiteralPath $LogPath) {
    Get-Content -LiteralPath $LogPath -Tail 30
  } else {
    Write-Host "No watcher log yet at $LogPath (is the watcher running?)"
  }
}

if (-not $InstallWatcher -and -not $UninstallWatcher -and -not $BuildEWIndex -and -not $TestCanary) {
  Write-Host @"
Usage:
  powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`" -InstallWatcher
  powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`" -UninstallWatcher
  powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`" -BuildEWIndex
  powershell -ExecutionPolicy Bypass -File `"$PSCommandPath`" -TestCanary
"@
}
