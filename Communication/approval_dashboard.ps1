$DraftsDir = "D:\Infinite\Infinity\Communication\drafts"
$ApprovedDir = "D:\Infinite\Infinity\Communication\approved"

function Get-ColorCode($colorString) {
    switch -Regex ($colorString) {
        "(?i)green" { return "Green" }
        "(?i)yellow" { return "Yellow" }
        "(?i)red" { return "Red" }
        "(?i)black" { return "DarkGray" }
        default { return "White" }
    }
}

while ($true) {
    $drafts = Get-ChildItem -Path $DraftsDir -Filter "*.json"
    
    if ($drafts.Count -eq 0) {
        Write-Host "No pending drafts in queue." -ForegroundColor DarkGray
        Start-Sleep -Seconds 5
        continue
    }

    foreach ($draftFile in $drafts) {
        Clear-Host
        $draft = Get-Content $draftFile.FullName -Raw | ConvertFrom-Json
        
        $riskColor = Get-ColorCode $draft.risk_assessment.color
        
        Write-Host "=================================================="
        Write-Host "                COMMUNICATION DRAFT               "
        Write-Host "=================================================="
        Write-Host ""
        Write-Host "EXPERIMENT: " -NoNewline; Write-Host $draft.experiment_id -ForegroundColor Cyan
        Write-Host "PLATFORM:   " -NoNewline; Write-Host $draft.platform -ForegroundColor Cyan
        Write-Host "INTENT:     " -NoNewline; Write-Host $draft.intent -ForegroundColor White
        Write-Host ""
        Write-Host "--- RISK ASSESSMENT ---" -ForegroundColor $riskColor
        Write-Host "COLOR:      " -NoNewline; Write-Host $draft.risk_assessment.color -ForegroundColor $riskColor
        Write-Host "REASONING:  " -NoNewline; Write-Host $draft.risk_assessment.reasoning -ForegroundColor $riskColor
        Write-Host ""
        Write-Host "--- DRAFT CONTENT ---"
        Write-Host $draft.content -ForegroundColor White
        Write-Host "--------------------------------------------------"
        Write-Host ""
        
        $validChoices = @("A", "R", "S", "E")
        $choice = ""
        while ($choice -notin $validChoices) {
            $choice = Read-Host "[A]pprove  [R]eject  [S]kip  [E]dit"
            $choice = $choice.ToUpper()
        }

        if ($choice -eq "A") {
            $draft.status = "approved"
            $draft | ConvertTo-Json -Depth 5 | Set-Content $draftFile.FullName -Encoding UTF8
            Move-Item -Path $draftFile.FullName -Destination $ApprovedDir -Force
            Write-Host "Draft Approved and moved to actuation queue." -ForegroundColor Green
            Start-Sleep -Seconds 1
        }
        elseif ($choice -eq "R") {
            Remove-Item -Path $draftFile.FullName -Force
            Write-Host "Draft Rejected and deleted." -ForegroundColor Red
            Start-Sleep -Seconds 1
        }
        elseif ($choice -eq "E") {
            Write-Host "Opening in Notepad..." -ForegroundColor Yellow
            Start-Process "notepad.exe" $draftFile.FullName -Wait
            Write-Host "Reloading..."
            Start-Sleep -Seconds 1
            # The while loop will just pick it up again on the next pass
            break 
        }
        elseif ($choice -eq "S") {
            Write-Host "Skipping draft." -ForegroundColor Yellow
            Start-Sleep -Seconds 1
        }
    }
}
