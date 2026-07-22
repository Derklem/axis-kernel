param (
    [Parameter(Mandatory=$true)]
    [string]$DraftFile
)

$draft = Get-Content $DraftFile -Raw | ConvertFrom-Json

Write-Host "1. Open Discord and go to the target server/channel."
Write-Host "2. Paste the content and send the message."
Write-Host "3. Right click the message and select 'Copy Message Link' (or copy the Message ID)."
Write-Host ""

$inputRef = Read-Host "Paste the resulting Discord link/ID here (or type [S]kip, [R]eject)"

if ($inputRef.ToUpper() -eq "S" -or $inputRef.ToUpper() -eq "R") {
    Write-Output $inputRef.ToUpper()
    exit
}

if ($inputRef -match "^https?://(www\.)?(discord\.com|discordapp\.com)/channels/\d+/\d+/\d+([?#].*)?$" -or $inputRef -match "^\d{17,20}$") {
    Write-Output $inputRef
} else {
    Write-Error "Invalid reference format for Discord."
}
