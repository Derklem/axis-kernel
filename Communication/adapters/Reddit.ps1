param (
    [Parameter(Mandatory=$true)]
    [string]$DraftFile
)

$draft = Get-Content $DraftFile -Raw | ConvertFrom-Json

Write-Host "1. Go to https://reddit.com"
Write-Host "2. Find the target subreddit, create a new post, and paste the content."
Write-Host "3. Post it, then copy the permalink to the post."
Write-Host ""

$inputRef = Read-Host "Paste the resulting Reddit URL here (or type [S]kip, [R]eject)"

if ($inputRef.ToUpper() -eq "S" -or $inputRef.ToUpper() -eq "R") {
    Write-Output $inputRef.ToUpper()
    exit
}

if ($inputRef -match "^https?://(www\.)?(reddit\.com|redd\.it)/.+") {
    Write-Output $inputRef
} else {
    Write-Error "Invalid URL format for Reddit."
}
