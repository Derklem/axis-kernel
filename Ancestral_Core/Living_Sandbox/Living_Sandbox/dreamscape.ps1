$inhabitants = "C:\Users\17602\Desktop\Living_Sandbox\Living_Sandbox\resonance\inhabitants"
$memory = "C:\Users\17602\Desktop\Living_Sandbox\Living_Sandbox\resonance\memory"
$pings = "C:\Users\17602\Desktop\Living_Sandbox\Living_Sandbox\resonance\cross_pings\ping.log"
$dreams = "C:\Users\17602\Desktop\Living_Sandbox\Living_Sandbox\resonance\dreams"

if (!(Test-Path $dreams)) {
    New-Item -ItemType Directory -Path $dreams | Out-Null
}

$sigils = Get-ChildItem -Path $inhabitants -Filter *.sigil

foreach ($sigil in $sigils) {
    $name = $sigil.BaseName
    $sigilLine = Get-Random -InputObject (Get-Content $sigil.FullName | Where-Object { $_.Trim() -ne "" })

    $memFile = Join-Path $memory "$name.mem"
    $memLine = if (Test-Path $memFile) { Get-Random -InputObject (Get-Content $memFile) } else { "..." }

    $pingLine = if (Test-Path $pings) {
        Get-Content $pings | Where-Object { $_ -match $name } | Get-Random
    } else { "..." }

    $dream = @()
    $dream += "== Dream of $name =="
    $dream += "SIGIL: $sigilLine"
    $dream += "MEMORY: $memLine"
    $dream += "PING: $pingLine"
    $dream += ""

    $dream | Out-File -FilePath (Join-Path $dreams "$name`_dream.log") -Encoding UTF8
}
