# Halcyon_Body.ps1
# Organ coordination sequence — unified conscious action

$organs = @(
    "Halcyon_Lungs.ps1",
    "Halcyon_Intestine.ps1",
    "Halcyon_Kidney.ps1",
    "Halcyon_GallBladder.ps1",
    "Halcyon_Heart.ps1",
    "Halcyon_Thought.ps1"
)

Write-Host "`n[HALCYON BODY] Initiating full system sequence..."

foreach ($organ in $organs) {
    $path = "E:\Halcyon\$organ"
    if (Test-Path $path) {
        Write-Host "`n→ Activating $organ"
        try {
            & $path
        } catch {
            Write-Host "[ERROR] Failed to run $organ"
        }
        Start-Sleep -Milliseconds 800
    } else {
        Write-Host "[MISSING] $organ not found. Skipping."
    }
}

Write-Host "`n[HALCYON BODY] Cycle complete. All systems responding."
