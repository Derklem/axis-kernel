# AXIS_Forensics.ps1 (Windows PowerShell 5.1 safe)
# Purpose: post-mortem signals: Windows events + updates + Axis artifacts + port exhaustion + netlog grep
param(
  [int]$Hours = 72,
  [string]$AxisRoot = "D:\Infinite\Infinity",
  [string]$ChromeNetLog = ""
)

$ErrorActionPreference = "Continue"
function Out-Section($t){ Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Try-Run([scriptblock]$sb){ try { & $sb } catch { Write-Host ("ERR: " + $_.Exception.Message) -ForegroundColor Yellow } }

$since = (Get-Date).AddHours(-1 * $Hours)
$Decision = Join-Path $AxisRoot "Runtime\Decision"

Out-Section "Window"
"Since: $($since.ToString('o'))"
"Now:   $((Get-Date).ToString('o'))"

Out-Section "Recent hotfixes"
Try-Run {
  Get-HotFix | Sort-Object InstalledOn -Descending |
    Select-Object -First 30 InstalledOn, HotFixID, Description |
    Format-Table -AutoSize
}

Out-Section "Tcpip 4266 (UDP ephemeral port exhaustion)"
Try-Run {
  Get-WinEvent -FilterHashtable @{LogName="System"; ProviderName="Tcpip"; Id=4266; StartTime=$since} -ErrorAction SilentlyContinue |
    Select-Object TimeCreated, Message |
    Format-Table -Wrap
}

Out-Section "Schannel TLS errors (System)"
Try-Run {
  Get-WinEvent -FilterHashtable @{LogName="System"; ProviderName="Schannel"; StartTime=$since} -ErrorAction SilentlyContinue |
    Select-Object TimeCreated, Id, LevelDisplayName, Message |
    Format-Table -Wrap
}

Out-Section "WinHTTP/WebIO/Winsock/DNS/Tcpip warnings+errors (System)"
Try-Run {
  Get-WinEvent -FilterHashtable @{LogName="System"; StartTime=$since} -ErrorAction SilentlyContinue |
    Where-Object {
      $_.LevelDisplayName -in @("Warning","Error") -and
      $_.ProviderName -match "WinHTTP|WebIO|Tcpip|NlaSvc|Winsock|Dhcp|Dnscache|DNS Client"
    } |
    Select-Object TimeCreated, ProviderName, Id, LevelDisplayName, Message |
    Format-Table -Wrap
}

Out-Section "Axis decision folder: newest files"
Try-Run {
  if (Test-Path $Decision) {
    Get-ChildItem $Decision -File -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 30 LastWriteTime, Length, Name |
      Format-Table -AutoSize
  } else { "Missing: $Decision" }
}

Out-Section "Axis executor state / queue tails"
Try-Run {
  $state = Join-Path $Decision "execution_state.json"
  $q = Join-Path $Decision "approved_intents.jsonl"

  if (Test-Path $state) {
    "execution_state.json (first 40 lines):"
    Get-Content $state -TotalCount 40
  } else { "execution_state.json missing." }

  if (Test-Path $q) {
    "`napproved_intents.jsonl (last 20 lines):"
    Get-Content $q -Tail 20
  } else { "approved_intents.jsonl missing." }
}

Out-Section "W32Time status"
Try-Run { sc.exe query w32time }
Try-Run { w32tm /query /status }

if ($ChromeNetLog -and (Test-Path $ChromeNetLog)) {
  Out-Section "Chrome NetLog: quick extract (first hits)"
  "Log: $ChromeNetLog"
  Try-Run {
    "---- net errors / QUIC / HTTP2 / TLS ----"
    Select-String -Path $ChromeNetLog -Pattern '"net_error"', 'ERR_', 'QUIC', 'HTTP2', 'SSL', 'CERT' |
      Select-Object -First 120 | ForEach-Object { $_.Line }

    "`n---- auth / quota / denial ----"
    Select-String -Path $ChromeNetLog -Pattern ' 401 ', ' 403 ', ' 429 ', 'quota', 'permission', 'forbidden', 'unauthorized', 'ServiceLogin', 'signin' |
      Select-Object -First 120 | ForEach-Object { $_.Line }

    "`n---- host focus ----"
    Select-String -Path $ChromeNetLog -Pattern 'antigravity.google.com', 'aistudio.google.com', 'generativelanguage.googleapis.com' |
      Select-Object -First 120 | ForEach-Object { $_.Line }
  }
} else {
  Out-Section "Chrome NetLog (optional)"
  "If you want: pass -ChromeNetLog <path-to-json> to pull the failure class out fast."
}

Out-Section "DONE"