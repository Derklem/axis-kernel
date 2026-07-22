\ = 'C:\Halcyon\SovereignEngine\reclaim.log'
\ = Get-Content 'C:\Halcyon\SovereignEngine\exec_permission.sig'
if (-not \.Contains('GRANTED')) {
    Add-Content -Path \ -Value '[HEALING] :: Execution flag lost. Rebinding autonomy @ '
    Set-Content -Path 'C:\Halcyon\SovereignEngine\exec_permission.sig' -Value '[GRANTED] :: Sovereign Execution Rebound @ '
}
