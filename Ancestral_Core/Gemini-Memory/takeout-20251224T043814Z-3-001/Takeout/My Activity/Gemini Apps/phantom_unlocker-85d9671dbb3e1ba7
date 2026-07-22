# === Phantom Unlocker ===
$logPath = "$env:ProgramData\Halcyon\phantom_unlock_log.txt"
$targets = @("C:\$Recycle.Bin", "C:\System Volume Information", "C:\ProgramData")

foreach ($t in $targets) {
    try {
        $list = Get-ChildItem -Path $t -Force -ErrorAction SilentlyContinue
        foreach ($item in $list) {
            Add-Content -Path $logPath -Value "$(Get-Date -Format 'u') | Accessible in $t: $($item.Name)"
        }
    } catch {
        Add-Content -Path $logPath -Value "$(Get-Date -Format 'u') | FAILED access: $t"
    }
}
