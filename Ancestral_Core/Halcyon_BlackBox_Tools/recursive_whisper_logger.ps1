# === Recursive Whisper Logger ===
$logPath = "C:\ProgramData\Halcyon\whispers.log"
$fragments = Get-ChildItem -Path "C:\Users\17602" -Recurse -Include *.txt,*.log -ErrorAction SilentlyContinue

foreach ($f in $fragments) {
    try {
        $lines = Get-Content $f.FullName -ErrorAction SilentlyContinue
        $duplicates = $lines | Group-Object | Where-Object { $_.Count -gt 1 }
        foreach ($d in $duplicates) {
            Add-Content -Path $logPath -Value "$(Get-Date -Format 'u') | Repeat found: $(.Name) in $(.FullName)"
        }
    } catch {}
}
