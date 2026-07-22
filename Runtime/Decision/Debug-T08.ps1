# Debug Imports
$ImmuneModule = "D:\Infinite\Infinity\Truth_Engine\Immune_Kernel.psm1"
if (Test-Path $ImmuneModule) { Import-Module $ImmuneModule -Force; Write-Host "Immune OK" }

$ProvenanceModule = "D:\Infinite\Infinity\Truth_Engine\T12_Provenance.psm1"
if (Test-Path $ProvenanceModule) { Import-Module $ProvenanceModule -Force; Write-Host "Prov OK" }

$PredictorModule = "D:\Infinite\Infinity\Truth_Engine\T13_Predictor.psm1"
if (Test-Path $PredictorModule) { Import-Module $PredictorModule -Force; Write-Host "Pred OK" }

function Ensure-RealityHeader { param($obj) return $obj }
Write-Host "Helpers OK"

function Get-TransportState {
    $tsFile = "D:\Infinite\Infinity\Runtime\Decision\transport_state.json"
    if (Test-Path $tsFile) {
        try { return (Get-Content $tsFile -Raw | ConvertFrom-Json) } catch { return $null }
    }
    return $null
}
Write-Host "Transport Helper OK"
