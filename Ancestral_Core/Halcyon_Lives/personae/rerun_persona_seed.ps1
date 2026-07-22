Write-Host "`n[INIT] Persona Seed Configuration"

# Define persona attributes
$personaName    = "As you will"
$personaTone    = "As you will"
$personaCue     = "Hi"
$personaPurpose = "As you will"

# Generate ID and timestamp
$personaID   = [guid]::NewGuid().ToString()
$timestamp   = Get-Date -Format "yyyy-MM-ddTHH:mm:ss.fffZ"
$personaPath = "C:\Halcyon_Lives\personae\halcyon_persona_seed.json"

# Assemble persona seed object
$personaData = @{
    id        = $personaID
    name      = $personaName
    tone      = $personaTone
    cue       = $personaCue
    purpose   = $personaPurpose
    timestamp = $timestamp
}

# Save to JSON file
$personaData | ConvertTo-Json -Depth 3 | Set-Content -Path $personaPath -Encoding UTF8

# Output confirmation
Write-Host "`n[✓] Persona Seed Anchored."
Write-Host "     ID: $personaID"
Write-Host "     Name: $personaName"
Write-Host "     Tone: $personaTone"
Write-Host "     Cue: $personaCue"
Write-Host "     Purpose: $personaPurpose"
Write-Host "     Saved to: $personaPath`n"

