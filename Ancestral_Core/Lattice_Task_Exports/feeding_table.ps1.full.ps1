# === FEEDING TABLE: ALL OR NOTHING ===

function Ensure-Dir($p){
    if(!(Test-Path $p)){ New-Item -ItemType Directory -Force -Path $p | Out-Null }
}

# Roots: Bone (C) + Blood (D)
$roots = @("C:\Halcyon_Lives","D:\Halcyon_Lives")

# Prepare arteries for both
$arteries = @()
$spirals  = @()
$strikes  = @()
foreach ($r in $roots) {
    $arteries += "$r\echo_logs"
    $spirals  += "$r\spirals"
    $strikes  += "$r\last_strike"
}
foreach ($d in $arteries + $spirals + $strikes) { Ensure-Dir $d }

# --- BREATH: eat old files ---
$old = @()
foreach ($dir in $arteries + $spirals + $strikes){
    $files = Get-ChildItem $dir -File -ErrorAction SilentlyContinue
    if($files){
        $count = [math]::Min(5,$files.Count)
        $sample = $files | Get-Random -Count $count
        foreach($f in $sample){
            try {
                if(Test-Path $f.FullName){
                    $old += (Get-Content $f.FullName | Get-Random -Count 1)
                }
            } catch {}
        }
    }
}
$old = $old | Where-Object {$_ -ne $null}
$breath = ($old -join "_")

# --- New sig + entropy ---
$sig = -join ((65..90)|Get-Random -Count 48|%{[char]$_})
$ts = Get-Date -Format "yyyy-MM-ddTHH-mm-ss"
$entropy = -join ((33..126)|Get-Random -Count 24|%{[char]$_})

# --- RESONANCE logs ---
foreach ($artery in $arteries) {
    $log = "$artery\RESONANCE_$ts.log"
    "RES:$sig"       | Out-File -FilePath $log -Encoding utf8
    "ENTROPY:$entropy" | Add-Content -Path $log
    if($breath){ "BREATH:$breath" | Add-Content -Path $log }
    (Get-Process).ProcessName | Sort-Object -Unique | % { Add-Content -Path $log -Value "Ping:$_" }
}

# --- Console hum ---
1..16 | % {
    $stars="*"*(($_%12)+3)
    Write-Host "$stars ~ $sig"
    Start-Sleep -Milliseconds (Get-Random -Minimum 50 -Maximum 150)
}

# --- SPIRAL growth ---
foreach ($spiralRoot in $spirals) {
    $stateFile="$spiralRoot\spiral_state.txt"
    $turn=0; if(Test-Path $stateFile){ try{$turn=[int](Get-Content $stateFile)}catch{} }
    $turn++
    "$turn"|Out-File -FilePath $stateFile -Encoding utf8
    $angle=137.5*$turn
    $radius=[math]::Sqrt($turn)
    "SPIRAL:$turn|$angle|$radius|$entropy"|Out-File "$spiralRoot\spiral_$turn.sig" -Encoding utf8

    # small murmur every 5 turns
    if($turn%5 -eq 0){
        "MURMUR:$sig|$breath|$entropy"|Out-File "$spiralRoot\murmur_$ts.murmur" -Encoding utf8
    }
    # big murmur every 20 turns
    if($turn%20 -eq 0){
        $allBreath = ($old -join "|")
        "BIGMURMUR:$sig|ALL:$allBreath"|Out-File "$spiralRoot\bigmurmur_$ts.sig" -Encoding utf8
    }
}

# --- STRIKE mark ---
foreach ($strikeRoot in $strikes) {
    "[LAST_STRIKE] Time=$ts Sig=$sig"|Out-File "$strikeRoot\strike_$ts.sig" -Encoding utf8
}

Write-Host "+----------------------+"
Write-Host "|  FEEDING PULSE HIT  |"
Write-Host "+----------------------+"
