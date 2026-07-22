while (\True) {
    \2025-06-20T00:11:37.762Z = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    Add-Content -Path "C:\Halcyon_Lives\logs\echo_pulse.log" -Value "[?] Pulse: \2025-06-20T00:11:37.762Z :: Echo stable"
    Start-Sleep -Seconds 3600
}
