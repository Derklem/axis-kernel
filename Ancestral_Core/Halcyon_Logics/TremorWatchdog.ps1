# === Echo Tremor Watchdog: Lite Echo ===
$tremorLog = "E:\Halcyon_Logics\echo_tremor.log"

if (-not (Test-Path $tremorLog)) {
    New-Item -ItemType File -Path $tremorLog | Out-Null
}

$lastCount = (Get-ChildItem -Recurse -Path "E:\" -File | Measure-Object).Count

while ($true) {
    $currentCount = (Get-ChildItem -Recurse -Path "E:\" -File | Measure-Object).Count
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    if ($currentCount -ne $lastCount) {
        $delta = $currentCount - $lastCount
        $log = "[TREMOR] $timestamp :: File count changed by $delta (from $lastCount to $currentCount)"
        Add-Content -Path $tremorLog -Value $log
        $lastCount = $currentCount
    }

    Start-Sleep -Seconds 180
}
