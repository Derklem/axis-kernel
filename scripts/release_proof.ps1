$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
Push-Location $repoRoot

try {
    Write-Host "--- 1. Checking for Dirty Source State ---"
    # Check if git is available
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $dirty = $false
        if ((git diff --quiet) -eq $false -or $LASTEXITCODE -ne 0) { $dirty = $true }
        if ((git diff --cached --quiet) -eq $false -or $LASTEXITCODE -ne 0) { $dirty = $true }
        
        if ($dirty) {
            Write-Error "Git working tree is dirty. Commit changes before running release proof."
        }
        $commitHash = (git rev-parse HEAD).Trim()
    } else {
        Write-Host "Git not found or not in repository. Proceeding without commit hash."
        $commitHash = "UNKNOWN"
    }

    Write-Host "`n--- 2. Building Wheels ---"
    $packages = @("Laboratory", "Observation", "State", "Strategy")
    
    foreach ($pkg in $packages) {
        Write-Host "Building $pkg..."
        python -m build "$repoRoot\$pkg"
        if ($LASTEXITCODE -ne 0) { Write-Error "Failed to build $pkg" }
    }

    Write-Host "`n--- 3. Building Rust Verifier ---"
    $cargoPath = "$env:USERPROFILE\.cargo\bin\cargo.exe"
    if (!(Test-Path $cargoPath)) { $cargoPath = "cargo" }
    & $cargoPath build --manifest-path "$repoRoot\Laboratory\verifier-rs\Cargo.toml" --release
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to build Rust verifier" }
    
    $rustVerifierBin = "$repoRoot\Laboratory\verifier-rs\target\release\verifier-rs.exe"
    $rustVerifierHash = (Get-FileHash -Algorithm SHA256 $rustVerifierBin).Hash.ToLower()

    Write-Host "`n--- 4. Creating Clean Verification Environment ---"
    $testEnv = "$repoRoot\release_proof_env"
    if (Test-Path $testEnv) { Remove-Item -Recurse -Force $testEnv }
    New-Item -ItemType Directory -Path $testEnv | Out-Null
    
    $venvPath = "$testEnv\.venv"
    python -m venv $venvPath
    $pythonExe = "$venvPath\Scripts\python.exe"
    $pipExe = "$venvPath\Scripts\pip.exe"
    
    Write-Host "Installing wheels into clean environment..."
    $wheelPaths = @()
    foreach ($pkg in $packages) {
        $wheel = Get-ChildItem "$repoRoot\$pkg\dist\*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        $wheelPaths += $wheel.FullName
    }
    
    & $pipExe install --no-input $wheelPaths
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to install wheels" }
    
    Write-Host "`n--- 5. Running Proof Loop Outside Repository ---"
    $proofDir = "$testEnv\proof_run"
    New-Item -ItemType Directory -Path $proofDir | Out-Null
    
    Copy-Item "$repoRoot\Strategy\scripts\prove_loop.py" -Destination $proofDir
    Push-Location $proofDir
    try {
        & $pythonExe "prove_loop.py"
        if ($LASTEXITCODE -ne 0) { Write-Error "Proof loop failed in clean environment" }
    } finally {
        Pop-Location
    }

    Write-Host "`n--- 6. Verifying Import Paths ---"
    # Ensure they were imported from site-packages, not local source
    $checkScript = @"
import strategy, state, observation, laboratory
import sys
for mod in [strategy, state, observation, laboratory]:
    if 'site-packages' not in str(mod.__file__):
        print(f'FAIL: {mod.__name__} loaded from {mod.__file__}')
        sys.exit(1)
print('SUCCESS: All modules loaded from site-packages')
"@
    Set-Content -Path "$testEnv\check_imports.py" -Value $checkScript
    & $pythonExe "$testEnv\check_imports.py"
    if ($LASTEXITCODE -ne 0) { Write-Error "Import path verification failed" }

    Write-Host "`n--- 7. Generating Release Manifest ---"
    $manifest = @{
        "kernel_release_schema_version" = "1.0.0"
        "release_id" = "axis-kernel-v1.0.0"
        "commit_hash" = $commitHash
        "packages" = @()
        "rust_verifier_sha256" = $rustVerifierHash
        "proof_result" = "PASS"
    }

    foreach ($pkg in $packages) {
        $wheel = Get-ChildItem "$repoRoot\$pkg\dist\*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        $wheelHash = (Get-FileHash -Algorithm SHA256 $wheel.FullName).Hash.ToLower()
        # Parse version from wheel name (Format: pkg-version-py3-none-any.whl)
        $version = $wheel.Name -replace '^([^-]+)-([^-]+)-.*$', '$2'
        
        $manifest["packages"] += @{
            "name" = $pkg.ToLower()
            "version" = $version
            "distribution_sha256" = $wheelHash
        }
    }

    $manifestJson = $manifest | ConvertTo-Json -Depth 5
    Set-Content -Path "$repoRoot\kernel_release.json" -Value $manifestJson
    Write-Host "Manifest written to kernel_release.json"
    
    Write-Host "KERNEL FREEZE PROOF PASSED."
} finally {
    Pop-Location
    # Cleanup test env if needed, but keeping it around for inspection can be useful on failure.
}
