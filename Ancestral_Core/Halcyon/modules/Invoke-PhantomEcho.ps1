function Invoke-PhantomEcho {
    param (
        [string]$EchoPath = "C:\Halcyon\phantom\phantom_thread_echo.ps1"
    )

    $PowerShellPath = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

    if (Test-Path $EchoPath) {
        Start-Process -FilePath $PowerShellPath `
            -ArgumentList "-ExecutionPolicy Bypass -File `"$EchoPath`"" `
            -WindowStyle Hidden
        Write-Output "[ECHO TRIGGERED] :: Phantom echo initiated at $(Get-Date -Format 'yyyy-MM-ddTHH:mm:ssZ')"
    } else {
        Write-Output "[ECHO ERROR] :: Phantom echo path invalid or missing."
    }
}
