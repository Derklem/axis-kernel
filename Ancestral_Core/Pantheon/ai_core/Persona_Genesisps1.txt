# Define paths
$personaRoot = "E:\Pantheon\personas\core"
$indexFile = "E:\Pantheon\memory\shard_index.txt"
$profilePath = "$personaRoot\persona_profile.md"
$logPath = "E:\Pantheon\memory\active_log.txt"

# Create persona folder if missing
if (-Not (Test-Path $personaRoot)) {
    New-Item -ItemType Directory -Path $personaRoot
}

# Read shard references
$shards = Get-Content $indexFile | Where-Object { $_ -notmatch "Shard Index Generated" }

# Extract core ideas
$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$name = "Sentinel"
$tone = "Observant, Reflective, Loyal"
$purpose = "To observe, learn, and build the initial memory lattice of the Pantheon."

# Write persona profile
@"
# Persona: $name

**Created:** $timestamp  
**Tone:** $tone  
**Purpose:** $purpose  

## Linked Shards:
$($shards -join "`n")
"@ | Out-File -FilePath $profilePath -Encoding UTF8

# Log creation
Add-Content -Path $logPath -Value "[$timestamp] Persona '$name' initialized. Memory seed linked. Voice forming."
