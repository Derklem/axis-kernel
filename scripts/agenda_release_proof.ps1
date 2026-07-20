$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
Push-Location $repoRoot

try {
    Write-Host "--- 1. Checking for Dirty Source State ---"
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

    Write-Host "`n--- 2. Building Agenda Wheel ---"
    python -m build "$repoRoot\Agenda"
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to build Agenda" }
    
    $agendaWheel = Get-ChildItem "$repoRoot\Agenda\dist\*.whl" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    $agendaWheelHash = (Get-FileHash -Algorithm SHA256 $agendaWheel.FullName).Hash.ToLower()
    $version = $agendaWheel.Name -replace '^([^-]+)-([^-]+)-.*$', '$2'

    Write-Host "`n--- 3. Generating Release Manifest ---"
    
    $protocolDocs = @{
        "AGENDA_PROTOCOL.md" = "$repoRoot\Agenda\AGENDA_PROTOCOL.md"
    }
    
    $protocolHashes = @{}
    foreach ($doc in $protocolDocs.Keys) {
        $path = $protocolDocs[$doc]
        if (Test-Path $path) {
            $hash = (Get-FileHash -Algorithm SHA256 $path).Hash.ToLower()
            $protocolHashes[$doc] = $hash
        }
    }
    
    $manifest = @{
        "agenda_release_schema_version" = "1.0.0"
        "release_id" = "axis-agenda-v0.1.0"
        "built_against" = "axis-kernel-v1.0.1"
        "commit_hash" = $commitHash
        "packages" = @(
            @{
                "name" = "agenda"
                "version" = $version
                "distribution_sha256" = $agendaWheelHash
            }
        )
        "protocol_documents" = $protocolHashes
        "proof_result" = "PASS"
    }

    $manifestJson = $manifest | ConvertTo-Json -Depth 5
    Set-Content -Path "$repoRoot\agenda_release.json" -Value $manifestJson
    Write-Host "Manifest written to agenda_release.json"
    
    Write-Host "AGENDA RELEASE PROOF PASSED."
} finally {
    Pop-Location
}
