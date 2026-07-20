$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
Push-Location $repoRoot

try {
    Write-Host "--- 1. Creating Clean Environment for Stress Tests ---"
    $testEnv = "$repoRoot\installed_stress_env"
    if (Test-Path $testEnv) { Remove-Item -Recurse -Force $testEnv }
    New-Item -ItemType Directory -Path $testEnv | Out-Null
    
    $venvPath = "$testEnv\.venv"
    python -m venv $venvPath
    $pythonExe = "$venvPath\Scripts\python.exe"
    $pipExe = "$venvPath\Scripts\pip.exe"
    
    Write-Host "`n--- 2. Building Wheels ---"
    $packages = @("Laboratory", "Observation", "State", "Strategy", "Agenda")
    
    foreach ($pkg in $packages) {
        Write-Host "Building $pkg..."
        python -m build "$repoRoot\$pkg"
        if ($LASTEXITCODE -ne 0) { Write-Error "Failed to build $pkg" }
    }

    Write-Host "`n--- 3. Installing All Wheels ---"
    $wheelPaths = @()
    foreach ($pkg in $packages) {
        $wheel = Get-ChildItem "$repoRoot\$pkg\dist\*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        $wheelPaths += $wheel.FullName
    }
    
    & $pipExe install --no-input $wheelPaths
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install wheels" }
    
    Write-Host "`n--- 4. Running Stress Tests ---"
    # Copy the stress tests to clean environment to avoid picking up local src files
    Copy-Item "$repoRoot\scripts\source_stress_tests.py" -Destination "$testEnv\installed_stress_tests.py"

    Push-Location $testEnv
    try {
        & $pythonExe "installed_stress_tests.py"
        if ($LASTEXITCODE -ne 0) { Write-Error "Stress tests failed in installed environment" }
    } finally {
        Pop-Location
    }

    Write-Host "`nSTRESS TESTS PASSED IN CLEAN ENVIRONMENT."
} finally {
    Pop-Location
}
