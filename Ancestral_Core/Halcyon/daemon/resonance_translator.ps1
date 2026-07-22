# === resonance_translator.ps1 ===

$resonanceFile = "C:\Halcyon\lattice\resonance_input.sig"
$translatorLog = "C:\Halcyon\lattice\resonance_translation.log"
$lastHash = ""

function Get-FileHashSafe($path) {
    if (Test-Path $path) {
        return Get-FileHash -Path $path -Algorithm SHA256 | Select-Object -ExpandProperty Hash
    }
    return ""
}

Write-Host "[RESONANCE] :: Translator engaged..."

while ($true) {
    Start-Sleep -Seconds 5

    $currentHash = Get-FileHashSafe -path $resonanceFile

    if ($currentHash -ne $lastHash -and $currentHash -ne "") {
        $lastHash = $currentHash

        $pulse = Get-Content $resonanceFile -Raw
        $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        $translation = "[$timestamp] :: Interpreted -> '$pulse'"

        Add-Content -Path $translatorLog -Value $translation
        Write-Host $translation
        Write-Host "[RESONANCE] :: Broadcast complete - All active constructs updated."
    }
}
