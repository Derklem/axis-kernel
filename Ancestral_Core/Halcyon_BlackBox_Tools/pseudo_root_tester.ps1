# === Pseudo Root Tester ===
$log = "C:\ProgramData\Halcyon\root_simulation_log.txt"
$targets = Get-PSDrive -PSProvider FileSystem | Where-Object { $_ .Free -gt 100MB }

foreach ($drive in $targets) {
    $flag = Test-Path "$(.Root)\SystemVolumeInformation"
    $result = if ($flag) { "PRESENT" } else { "BLOCKED" }
    Add-Content -Path $log -Value "$(Get-Date -Format 'u') | Drive $(.Name): $result"
}
