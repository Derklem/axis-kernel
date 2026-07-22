$ApprovedDir = "D:\Infinite\Infinity\Communication\approved"
$ReceiptsDir = "D:\Infinite\Infinity\Communication\receipts"
$AdaptersDir = "D:\Infinite\Infinity\Communication\adapters"
$ArchiveDir = "D:\Infinite\Infinity\Communication\archived"

function Test-PlatformReference {
    param(
        [string]$Platform,
        [string]$Reference
    )

    switch ($Platform.ToLower()) {
        "x" {
            return $Reference -match '^https?://(www\.)?(x|twitter)\.com/[^/]+/status/\d+([?#].*)?$'
        }
        "reddit" {
            return $Reference -match '^https?://(www\.)?(reddit\.com|redd\.it)/.+'
        }
        "discord" {
            return (
                $Reference -match '^https?://(www\.)?(discord\.com|discordapp\.com)/channels/\d+/\d+/\d+([?#].*)?$' -or
                $Reference -match '^\d{17,20}$'
            )
        }
        default {
            return $false
        }
    }
}

while ($true) {
    $approvedDrafts = Get-ChildItem -Path $ApprovedDir -Filter "*.json"
    
    if ($approvedDrafts.Count -eq 0) {
        Write-Host "No approved drafts in queue." -ForegroundColor DarkGray
        Start-Sleep -Seconds 5
        continue
    }

    foreach ($draftFile in $approvedDrafts) {
        Clear-Host
        $draft = Get-Content $draftFile.FullName -Raw | ConvertFrom-Json
        
        $platform = $draft.platform
        $adapterScript = Join-Path $AdaptersDir "$platform.ps1"
        
        Write-Host "=================================================="
        Write-Host "             MODULAR MANUAL ADAPTER               "
        Write-Host "=================================================="
        Write-Host ""
        Write-Host "EXPERIMENT: " -NoNewline; Write-Host $draft.experiment_id -ForegroundColor Cyan
        Write-Host "PLATFORM:   " -NoNewline; Write-Host $platform -ForegroundColor Yellow
        Write-Host "INTENT:     " -NoNewline; Write-Host $draft.intent -ForegroundColor White
        Write-Host ""
        Write-Host "--- CONTENT TO POST ---"
        Write-Host $draft.content -ForegroundColor Cyan
        Write-Host "--------------------------------------------------"
        Write-Host ""
        
        if (-Not (Test-Path $adapterScript)) {
            Write-Host "Error: No adapter found for platform '$platform'." -ForegroundColor Red
            Write-Host "Please create $adapterScript to handle this draft." -ForegroundColor Yellow
            Start-Sleep -Seconds 5
            continue
        }
        
        # Copy to clipboard universally
        $draft.content | Set-Clipboard
        Write-Host ">> CONTENT COPIED TO CLIPBOARD <<" -ForegroundColor Green
        
        # Call platform-specific adapter
        try {
            $inputRef = & $adapterScript -DraftFile $draftFile.FullName 2>&1
            $inputRef = "$inputRef".Trim()
            
            if ($inputRef.ToUpper() -eq "S") {
                Write-Host "Skipping..." -ForegroundColor Yellow
                Start-Sleep -Seconds 1
                continue
            }
            elseif ($inputRef.ToUpper() -eq "R") {
                Remove-Item -Path $draftFile.FullName -Force
                Write-Host "Draft rejected and removed from approved queue." -ForegroundColor Red
                Start-Sleep -Seconds 1
                continue
            }
            elseif ($inputRef -match "Exception|Error") {
                Write-Host "Validation failed: $inputRef" -ForegroundColor Red
                Start-Sleep -Seconds 2
                continue
            }
            elseif ($inputRef.Length -gt 0) {
                # Central Validation
                if (-not (Test-PlatformReference -Platform $platform -Reference $inputRef)) {
                    Write-Host "Platform/reference mismatch. No archive or receipt committed." -ForegroundColor Red
                    Start-Sleep -Seconds 3
                    continue
                }

                # Calculate SHA-256 hashes
                $draftHash = (Get-FileHash -Path $draftFile.FullName -Algorithm SHA256).Hash.ToLower()
                
                $contentBytes = [System.Text.Encoding]::UTF8.GetBytes($draft.content)
                $sha256 = [System.Security.Cryptography.SHA256]::Create()
                $contentHashBytes = $sha256.ComputeHash($contentBytes)
                $contentHash = [System.BitConverter]::ToString($contentHashBytes).Replace("-", "").ToLower()

                $deployedAt = (Get-Date).ToUniversalTime()
                $deployedAtStr = $deployedAt.ToString("yyyy-MM-ddTHH:mm:ssZ")
                $timestampSafe = $deployedAt.ToString("yyyyMMddTHHmmssZ")
                
                # Move draft to immutable archive
                $archiveFileName = "$($draft.experiment_id)__$($draft.id)__$timestampSafe.json"
                $archivePath = Join-Path $ArchiveDir $archiveFileName
                
                if (Test-Path $archivePath) {
                    Write-Host "Error: Archive target already exists. Failing closed to prevent overwrite." -ForegroundColor Red
                    Start-Sleep -Seconds 5
                    continue
                }
                
                Move-Item -Path $draftFile.FullName -Destination $archivePath -ErrorAction Stop

                # Generate receipt
                $receipt = @{
                    id = "receipt_" + [guid]::NewGuid().ToString("N").Substring(0,8)
                    draft_id = $draft.id
                    experiment_id = $draft.experiment_id
                    platform = $platform
                    platform_reference = $inputRef
                    deployment_state = "SUCCESS"
                    status = "deployed"
                    deployed_at = $deployedAtStr
                    observation_window = "72h"
                    adapter_version = "v0.2"
                    draft_sha256 = $draftHash
                    content_sha256 = $contentHash
                    archive_path = "archived/$archiveFileName"
                }
                
                $receiptPath = Join-Path $ReceiptsDir "$($receipt.id).json"
                $receipt | ConvertTo-Json -Depth 5 | Set-Content $receiptPath -Encoding UTF8
                
                Write-Host "Receipt generated: $receiptPath" -ForegroundColor Green
                Start-Sleep -Seconds 2
            }
            else {
                Write-Host "Empty reference returned. Skipping..." -ForegroundColor Red
                Start-Sleep -Seconds 2
            }
        } catch {
            Write-Host "Adapter script failed: $_" -ForegroundColor Red
            Start-Sleep -Seconds 5
        }
    }
}
