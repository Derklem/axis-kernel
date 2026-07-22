# === Symbolic Entry Trigger ===
$paths = Get-ChildItem -Path "C:\Users\17602" -Recurse -Include *.sigil,*.seed,*.trace -ErrorAction SilentlyContinue
$log = "C:\ProgramData\Halcyon\trigger_log.txt"
foreach ($p in $paths) {
    Add-Content -Path $log -Value "$(Get-Date -Format 'u') | Triggered: $(.FullName)"
}
