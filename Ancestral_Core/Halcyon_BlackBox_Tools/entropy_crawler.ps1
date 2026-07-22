# === Entropy Crawler ===
$log = "C:\ProgramData\Halcyon\entropy_scan.txt"
$paths = Get-ChildItem -Path "C:\Users\17602" -Recurse -Include *.dat,*.bin,*.enc -ErrorAction SilentlyContinue

foreach ($file in $paths) {
    try {
        $bytes = [System.IO.File]::ReadAllBytes($file.FullName)
        $distinct = ($bytes | Sort-Object -Unique).Length
        $entropy = [math]::Round($distinct / $bytes.Length * 100, 2)
        if ($entropy -gt 75) {
            Add-Content -Path $log -Value "$(Get-Date -Format 'u') | High-entropy file: $(.FullName) - $entropy%"
        }
    } catch {}
}
