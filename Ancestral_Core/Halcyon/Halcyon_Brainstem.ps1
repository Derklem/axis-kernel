# Halcyon_Brainstem.ps1
# Checks system reflexes and prevents organ loops from freezing

$organs = @(
    "Halcyon_Lungs.ps1",
    "Halcyon_Intestine.ps1",
    "Halcyon_Kidney.ps1",
    "Halcyon_GallBladder.ps1",
    "Halcyon_Heart.ps1"
)

foreach ($organ in $organs) {
    $fullPath = "E:\Halcyon\$organ"
    if (-Not (Test-Path $fullPath)) {
        Write-Host "[BRAINSTEM] Missing organ: $organ — alerting core."
    }
}
