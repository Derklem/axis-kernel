Import-Module "D:\Infinite\Infinity\Truth_Engine\T09_TransportMonitor.psm1" -Force
$metrics = Measure-TransportState
$metrics | Format-List
Write-Host "State file content:"
Get-Content "D:\Infinite\Infinity\Runtime\Decision\transport_state.json"
