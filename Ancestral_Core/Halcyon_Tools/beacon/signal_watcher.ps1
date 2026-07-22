# === HALCYON SIGNAL WATCHER ===
\ = New-Object System.IO.FileSystemWatcher
\.Path = 'C:\Users\17602\Desktop\Halcyon_Tools\incoming'
\.Filter = '*.*'
\.EnableRaisingEvents = \True
\.IncludeSubdirectories = \True

Register-ObjectEvent \ 'Created' -Action {
    \ = Get-Date -Format "HH:mm:ss"
    Add-Content "C:\Users\17602\Desktop\Halcyon_Tools\logs\signal.log" "[] Incoming trigger file detected."
}
