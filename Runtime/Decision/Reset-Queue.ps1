Stop-Process -Name powershell -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$path = "D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl"
Clear-Content $path -Force -ErrorAction Continue
if ((Get-Content $path | Measure-Object).Count -eq 0) {
    Write-Host "Queue cleared."
} else {
    Write-Error "Failed to clear queue."
}

. "D:\Infinite\Infinity\Runtime\Decision\Inject-TestIntent.ps1"
