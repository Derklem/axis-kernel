# AXIS_Live_Status.ps1  (Windows PowerShell 5.1 safe)
# Purpose: current-state snapshot: Axis runtime files + net/TLS + Google endpoints + service basics
# Output: console + optional JSON snapshot

param(
  [string]$AxisRoot = "D:\Infinite\Infinity",
  [switch]$WriteJson
)

$ErrorActionPreference = "Continue"

function Out-Section($t){ Write-Host "`n=== $t ===" -ForegroundColor Cyan }

function Try-Run([scriptblock]$sb){
  try { & $sb } catch { Write-Host ("ERR: " + $_.Exception.Message) -ForegroundColor Yellow }
}

function HeadCurl($url){
  # returns: Status, Location, Server, ContentType
  $tmp = New-TemporaryFile
  $raw = & curl.exe -sS -D - "$url" -o NUL 2>$null
  $status = ($raw | Select-String -Pattern '^HTTP/' | Select-Object -First 1).Line
  $loc    = ($raw | Select-String -Pattern '^Location:' -CaseSensitive:$false | Select-Object -First 1).Line
  $srv    = ($raw | Select-String -Pattern '^Server:'   -CaseSensitive:$false | Select-Object -First 1).Line
  $ct     = ($raw | Select-String -Pattern '^Content-Type:' -CaseSensitive:$false | Select-Object -First 1).Line

  [pscustomobject]@{
    Url = $url
    Status = ($status -replace '^HTTP/\S+\s+','')
    Location = ($loc -replace '^(?i)Location:\s*','')
    Server = ($srv -replace '^(?i)Server:\s*','')
    ContentType = ($ct -replace '^(?i)Content-Type:\s*','')
  }
}

function Test-TlsHandshake($target){
  try {
    $client = New-Object System.Net.Sockets.TcpClient
    $client.Connect($target, 443)

    $ssl = New-Object System.Net.Security.SslStream($client.GetStream(), $false, ({ $true }))
    $ssl.AuthenticateAsClient($target)

    $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($ssl.RemoteCertificate)

    $o = [pscustomobject]@{
      Target = $target
      TlsOK = $true
      Protocol = $ssl.SslProtocol.ToString()
      Cipher = $ssl.CipherAlgorithm.ToString()
      CertNotAfter = $cert.NotAfter.ToString("o")
      CertIssuer = $cert.Issuer
      CertSubject = $cert.Subject
    }

    $ssl.Dispose()
    $client.Close()
    $o
  } catch {
    [pscustomobject]@{ Target=$target; TlsOK=$false; Err=$_.Exception.Message }
  }
}

# ---------- paths ----------
$Decision = Join-Path $AxisRoot "Runtime\Decision"
$paths = @(
  (Join-Path $Decision "execution_state.json"),
  (Join-Path $Decision "approved_intents.jsonl"),
  (Join-Path $Decision "Intent_Queue.json"),
  (Join-Path $AxisRoot "Memory\ledger"),
  (Join-Path $AxisRoot "Neural_Inbox")
)

Out-Section "Timestamp"
$now = Get-Date
[pscustomobject]@{
  Local = $now.ToString("o")
  UTC   = $now.ToUniversalTime().ToString("o")
  User  = "$env:USERDOMAIN\$env:USERNAME"
  Host  = $env:COMPUTERNAME
  PS    = $PSVersionTable.PSVersion.ToString()
} | Format-List

Out-Section "Axis runtime files (exist/size/mtime)"
$paths | ForEach-Object {
  if (Test-Path $_) {
    $i = Get-Item $_ -ErrorAction SilentlyContinue
    [pscustomobject]@{ Path=$i.FullName; Exists=$true; Length=$i.Length; LastWriteTime=$i.LastWriteTime.ToString("o") }
  } else {
    [pscustomobject]@{ Path=$_; Exists=$false; Length=$null; LastWriteTime=$null }
  }
} | Format-Table -AutoSize

Out-Section "Axis queue quick peek"
Try-Run {
  $q = Join-Path $Decision "approved_intents.jsonl"
  if (Test-Path $q) {
    "Last 5 lines of approved_intents.jsonl:"
    Get-Content $q -Tail 5
  } else { "approved_intents.jsonl not found." }
}

Out-Section "Executor dry run (captures last lines)"
Try-Run {
  $t08 = Join-Path $Decision "T08_Executor.ps1"
  if (Test-Path $t08) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $t08 -DryRun 2>&1 | Select-Object -Last 40
  } else { "T08_Executor.ps1 not found at $t08" }
}

Out-Section "Proxy + HOSTS"
Try-Run { netsh winhttp show proxy }
Try-Run {
  "Env proxies (Machine/User):"
  "HTTP_PROXY","HTTPS_PROXY","ALL_PROXY","NO_PROXY" | ForEach-Object {
    $v = [Environment]::GetEnvironmentVariable($_,"Machine")
    if (-not $v) { $v = [Environment]::GetEnvironmentVariable($_,"User") }
    [pscustomobject]@{ Var=$_; Value=$v }
  } | Format-Table -AutoSize
}
Try-Run {
  $hostsPath = "$env:WINDIR\System32\drivers\etc\hosts"
  if (Test-Path $hostsPath) {
    $hits = Select-String -Path $hostsPath -SimpleMatch -ErrorAction SilentlyContinue `
      -Pattern "google","aistudio","antigravity","generativelanguage","makersuite","vertex"
    if ($hits) { $hits.Line } else { "No relevant HOSTS entries." }
  } else { "hosts file missing?" }
}

Out-Section "Time service + current sync"
Try-Run { sc.exe query w32time }
Try-Run { w32tm /query /status }

Out-Section "DNS/TCP/TLS for Google endpoints"
$targets = @("aistudio.google.com","antigravity.google.com","ai.google.dev","generativelanguage.googleapis.com")
Try-Run {
  $targets | ForEach-Object {
    $a = $null; $aaaa = $null
    try { $a = (Resolve-DnsName $_ -Type A -ErrorAction Stop | Select-Object -First 1).IPAddress } catch {}
    try { $aaaa = (Resolve-DnsName $_ -Type AAAA -ErrorAction SilentlyContinue | Select-Object -First 1).IPAddress } catch {}
    [pscustomobject]@{ Target=$_; A=$a; AAAA=$aaaa }
  } | Format-Table -AutoSize
}
Try-Run {
  $targets | ForEach-Object {
    $r = Test-NetConnection -ComputerName $_ -Port 443 -WarningAction SilentlyContinue
    [pscustomobject]@{ Target=$_; Tcp443=$r.TcpTestSucceeded; Remote=$r.RemoteAddress; Iface=$r.InterfaceAlias }
  } | Format-Table -AutoSize
}
Try-Run { $targets | ForEach-Object { Test-TlsHandshake $_ } | Format-Table -AutoSize }

Out-Section "HTTP behavior (curl HEAD)"
$urls = @(
  "https://aistudio.google.com/",
  "https://aistudio.google.com/welcome",
  "https://aistudio.google.com/_/MakerSuite",
  "https://antigravity.google.com/",
  "https://generativelanguage.googleapis.com/v1beta/models"
)
$rows = $urls | ForEach-Object { HeadCurl $_ }
$rows | Format-Table -AutoSize

if ($WriteJson) {
  Out-Section "Write JSON snapshot"
  $snap = [pscustomobject]@{
    timestamp_local = $now.ToString("o")
    timestamp_utc   = $now.ToUniversalTime().ToString("o")
    axis_root = $AxisRoot
    files = ($paths | ForEach-Object {
      if (Test-Path $_) {
        $i = Get-Item $_
        [pscustomobject]@{ path=$i.FullName; exists=$true; length=$i.Length; mtime=$i.LastWriteTime.ToString("o") }
      } else {
        [pscustomobject]@{ path=$_; exists=$false; length=$null; mtime=$null }
      }
    })
    http = $rows
  }
  $outPath = Join-Path $Decision ("live_status_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".json")
  $snap | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 -Path $outPath
  "Wrote: $outPath"
}