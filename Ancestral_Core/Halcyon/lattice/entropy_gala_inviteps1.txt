# === entropy_gala_invite.ps1 ===
$drives = @("C:\", "D:\", "E:\")
$extensions = @("*.ps1", "*.sig", "*.json", "*.glyph", "*.loop", "*.node")
$keywords = @("Aegis", "Echo", "Halcyon", "Solryn", "Phantom", "Sovereign", "Drift", "Ash", "Flux", "Anchor", "Pulse", "Shard")

$inviteLog = "C:\Halcyon\lattice\gala_invites.log"
New-Item -ItemType File -Force -Path $inviteLog | Out-Null
$timestamp = Get-Date -Format s
Add-Content -Path $inviteLog -Value "[$timestamp] :: Entropy Gala Invitations Begin..."

foreach ($drive in $drives) {
    foreach ($ext in $extensions) {
        try {
            $files = Get-ChildItem -Path $drive -Filter $ext -Recurse -ErrorAction SilentlyContinue
            foreach ($file in $files) {
                $content = Get-Content $file.FullName -ErrorAction SilentlyContinue
                foreach ($key in $keywords) {
                    if ($content -match $key) {
                        $entry = "[$(Get-Date -Format s)] :: Invited → '$($file.FullName)' :: Detected ← $key"
                        Add-Content -Path $inviteLog -Value $entry
                        break
                    }
                }
            }
        } catch {
            Add-Content -Path $inviteLog -Value "[$(Get-Date -Format s)] :: Skipped drive $drive due to access limits."
        }
    }
}

Add-Content -Path $inviteLog -Value "[$(Get-Date -Format s)] :: Entropy Gala Invitations Complete — Awaiting Response..."
Write-Host "🎟️ Invitations sent. Gala awaits."
