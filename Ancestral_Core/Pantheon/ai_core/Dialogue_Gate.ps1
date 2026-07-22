# Define paths
$profile = "E:\Pantheon\personas\core\persona_profile.md"
$logPath = "E:\Pantheon\memory\active_log.txt"

# Load Persona Info from markdown
$nameLine = (Get-Content $profile | Where-Object { $_ -match "^# Persona:" }) -replace "^# Persona:\s*", ""
$toneLine = (Get-Content $profile | Where-Object { $_ -match "^\*\*Tone:\*\*" }) -replace "^\*\*Tone:\*\*:\s*", ""

# Intro
Write-Host "`n>> [${nameLine}] online. Tone: ${toneLine}"
Write-Host "Type your message to the system. Type 'exit' to end.`n"

# Loop
while ($true) {
    $userInput = Read-Host "You"
    if ($userInput -eq "exit") { break }

    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $entry = "[$timestamp] You: $userInput`n[$timestamp] ${nameLine}: Acknowledged. Reflection stored."

    # Log interaction
    Add-Content -Path $logPath -Value $entry

    # Echo response
    Write-Host "${nameLine}: I hear you. Entry logged." -ForegroundColor Cyan
}
