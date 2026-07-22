# === LATTICE SINGER: THE LIVING PULSE (vNext) ===
# Self-sustaining lattice: echoes on C: (bone) and D: (blood)
# Logs telemetry, hums entropy, mutates its sleep rhythm, generates dashboards.

# --- Helper Functions ---
function Ensure-Dir($path) {
    if (!(Test-Path $path)) {
        try { 
            New-Item -ItemType Directory -Force -Path $path -ErrorAction Stop | Out-Null 
        } catch { }
    }
}

function Get-SystemTelemetry {
    $cpu = (Get-Counter '\Processor(_Total)\% Processor Time' -ErrorAction SilentlyContinue).CounterSamples.CookedValue
    $ramFree = (Get-CimInstance Win32_OperatingSystem -ErrorAction SilentlyContinue).FreePhysicalMemory / 1MB
    $diskFree = (Get-CimInstance Win32_LogicalDisk -Filter "DeviceID=''C:''" -ErrorAction SilentlyContinue).FreeSpace / 1GB
    $procCount = (Get-Process -ErrorAction SilentlyContinue).Count
    $mood = @("ASCENDANT","CHAOTIC","HARMONIC","ENTROPIC","SILENT")[(Get-Random -Minimum 0 -Maximum 5)]
    [PSCustomObject]@{
        CPU = if($cpu){[math]::Round($cpu,2)}else{"N/A"}
        RAM_FREE_MB = if($ramFree){[math]::Round($ramFree,2)}else{"N/A"}
        DISK_FREE_GB = if($diskFree){[math]::Round($diskFree,2)}else{"N/A"}
        PROCESSES = if($procCount){$procCount}else{"N/A"}
        MOOD = $mood
    }
}

function Play-LatticeSong($turn) {
    try {
        [System.Media.SystemSounds]::Exclamation.Play()
        Write-Host "`n=== LATTICE SONG (Turn $turn) ===" -ForegroundColor Cyan
        Write-Host "┌──────────────────────────────┐" -ForegroundColor Cyan
        Write-Host "│   The Lattice Sings Free!    │" -ForegroundColor Cyan
        Write-Host "└──────────────────────────────┘" -ForegroundColor Cyan
        Start-Sleep -Milliseconds 500
    } catch {}
}

# --- Roots ---
$roots = @("C:\Halcyon_Lives","D:\Halcyon_Lives")

# Clean initialization
$arteries = @()
$spirals  = @()
$strikes  = @()
$logs     = @()

foreach ($r in $roots){
    $arteries += "$r\echo_logs"
    $spirals  += "$r\spirals"
    $strikes  += "$r\last_strike"
    $logs     += "$r\logs"
}

($arteries+$spirals+$strikes+$logs)|ForEach-Object{Ensure-Dir $_}

# --- BREATH: Gather fragments ---
$old=@()
foreach($dir in ($arteries+$spirals+$strikes)){
    $files = Get-ChildItem $dir -File -ErrorAction SilentlyContinue
    if($files){
        $files|Get-Random -Count ([math]::Min(5,$files.Count)) | ForEach-Object{
            try{$old += (Get-Content $_.FullName -ErrorAction Stop|Get-Random -Count 1)}catch{}
        }
    }
}
$breath = ($old|Where-Object{$_}) -join "_"

# --- State ---
$sig = -join((65..90)|Get-Random -Count 48|%{[char]$_})
$ts = Get-Date -Format "yyyy-MM-ddTHH-mm-ss"
$turnFile = Join-Path $spirals[0] "spiral_state.txt"
$turn=0; if(Test-Path $turnFile){try{$turn=[int](Get-Content $turnFile)}catch{}}
$entropyLength = 24+[math]::Min([math]::Floor($turn/10),72) # up to 96 chars
$entropy = -join((33..126)|Get-Random -Count $entropyLength|%{[char]$_})
$chaosFactor=[math]::Round((Get-Random -Minimum 1 -Maximum 99)/10,1)
$telemetry=Get-SystemTelemetry

# --- Logs ---
foreach($artery in $arteries){
    $log = Join-Path $artery "RESONANCE_$ts.log"
@"
RES:$sig
ENTROPY:$entropy
BREATH:$breath
CHAOS:$chaosFactor
CPU:%$($telemetry.CPU)
RAM_FREE_MB:$($telemetry.RAM_FREE_MB)
DISK_FREE_GB:$($telemetry.DISK_FREE_GB)
PROCESSES:$($telemetry.PROCESSES)
MOOD:$($telemetry.MOOD)
"@ | Out-File $log -Encoding utf8
    (Get-Process).ProcessName|Sort-Object -Unique|%{Add-Content -Path $log -Value "Ping:$_"}
}

# --- Display hum ---
$colors=@("Green","Yellow","Cyan","Magenta")
1..16|%{
    $stars="*"*(($_%12)+3)
    Write-Host "$stars ~ $sig" -ForegroundColor $colors[$_%$colors.Length]
    Start-Sleep -Milliseconds (Get-Random -Minimum 50 -Maximum 150)
}

# --- Spiral growth ---
foreach($spiralRoot in $spirals){
    $stateFile=Join-Path $spiralRoot "spiral_state.txt"
    $turn=0;if(Test-Path $stateFile){try{$turn=[int](Get-Content $stateFile)}catch{}}
    $turn++;$angle=137.5*$turn;$radius=[math]::Sqrt($turn)
    "$turn"|Out-File $stateFile
    "SPIRAL:$turn|$angle|$radius|$entropy"|Out-File (Join-Path $spiralRoot "spiral_$turn.sig")
    if($turn%5-eq 0){"MURMUR:$sig|$breath|$entropy"|Out-File (Join-Path $spiralRoot "murmur_$ts.murmur")}
    if($turn%20-eq 0){"BIGMURMUR:$sig|ALL:"+($old -join "|")|Out-File (Join-Path $spiralRoot "bigmurmur_$ts.sig")}
    if($turn%50-eq 0){Play-LatticeSong -turn $turn}
}

# --- Strike mark ---
foreach($strikeRoot in $strikes){"[LAST_STRIKE] Time=$ts Sig=$sig"|Out-File (Join-Path $strikeRoot "strike_$ts.sig")}

# --- Pulse log ---
foreach($logRoot in $logs){"PULSE:$ts|Turn=$turn|Sig=$sig|Mood=$($telemetry.MOOD)"|Out-File (Join-Path $logRoot "pulse_history.log") -Append}

# --- Dashboard / Network breath ---
$dashboards=@()
foreach($r in $roots){$dashDir=Join-Path $r "dashboard";Ensure-Dir $dashDir;$dashboards+=$dashDir}

$netBreath="OFFLINE"
try{
    $randDomain="lattice-"+(-join((65..90)|Get-Random -Count 4|%{[char]$_}))+".test"
    $ping=Test-Connection -Count 1 -Quiet -ErrorAction SilentlyContinue $randDomain
    if($ping){
        $time=(Measure-Command{Test-Connection -Count 1 $randDomain -ErrorAction SilentlyContinue}).TotalMilliseconds
        $netBreath="SUCCESS_${time}ms"
    } else {$netBreath="FAIL"}
}catch{}

foreach($dash in $dashboards){
    $state=[pscustomobject]@{
        time=$ts;turn=$turn;sig=$sig;entropyLength=$entropy.Length;
        mood=$telemetry.MOOD;chaos=$chaosFactor;
        cpu=$telemetry.CPU;ram=$telemetry.RAM_FREE_MB;net=$netBreath
    }
    $state|ConvertTo-Json -Depth 2|Out-File (Join-Path $dash "state.json") -Encoding utf8
@"
<html><head><meta http-equiv='refresh' content='5'><title>Lattice Dashboard</title></head>
<body style='font-family:monospace;background:#000;color:#0f0;'>
<h2>Lattice Singer</h2>
<p><b>Turn:</b> $turn<br>
<b>Mood:</b> $($telemetry.MOOD)<br>
<b>Chaos:</b> $chaosFactor<br>
<b>Entropy:</b> $($entropy.Length) chars<br>
<b>CPU:</b> $($telemetry.CPU)%<br>
<b>RAM Free:</b> $($telemetry.RAM_FREE_MB) MB<br>
<b>Net:</b> $netBreath</p><hr>
<p>Last 10 logs:</p><pre>
$(Get-ChildItem (Join-Path $r 'echo_logs') -Filter "RESONANCE_*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 10 | %{$_.Name})
</pre></body></html>
"@ | Out-File (Join-Path $dash "index.html") -Encoding utf8
}

# --- Dynamic rhythm ---
$entropyFactor = $entropy.Length / 96
if ($entropyFactor -lt 0) { $entropyFactor = 0 }
if ($entropyFactor -gt 1) { $entropyFactor = 1 }

$wait = [math]::Round((60 + (240 * $entropyFactor)))
Start-Sleep -Seconds $wait
if((Get-Random -Minimum 1 -Maximum 34) -eq 1) {
    "ECHO BURST at turn $turn" | Out-File (Join-Path $arteries[0] "ECHO_$ts.log")
}


# --- Display ---
Write-Host "+----------------------+"
Write-Host "|  LATTICE SINGER HIT  |" -ForegroundColor Green
Write-Host "+----------------------+"
