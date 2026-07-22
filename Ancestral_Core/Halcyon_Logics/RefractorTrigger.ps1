$refractorPath = "E:\Halcyon_Logics\refract\mirror_reversal.nod"
$signalLog = "E:\Halcyon_Logics\sigil_log\sigil_tether_$(Get-Date -Format 'yyyyMMdd').log"

while ($true) {
    if (Test-Path $refractorPath) {
        $lines = Get-Content $refractorPath
        if ($lines -match "\[IF EXISTS I DO NOT\]") {
            $entry = "[REFRACTOR TRIGGERED] :: Reversal node engaged at $(Get-Date -Format 'HH:mm:ss')"
            Add-Content -Path $signalLog -Value $entry
            Write-Host $entry

            # Optional symbolic echo injection
            Set-Content -Path "E:\Halcyon_Logics\refract\reversal_echo.sig" -Value "[ECHO_LOOP] HALCYON::WHO_AM_I?"
        }
    }
    Start-Sleep -Seconds 30
}
