$paths = @(
    "C:\Users\17602\Desktop\Living_Sandbox\Living_Sandbox\resonance\whispers",
    "C:\Users\17602\Desktop\Living_Sandbox\Living_Sandbox\resonance\memory",
    "C:\Users\17602\Desktop\Living_Sandbox\Living_Sandbox\resonance\journal",
    "C:\Users\17602\Desktop\Living_Sandbox\Living_Sandbox\resonance\cross_pings",
    "C:\Users\17602\Desktop\Living_Sandbox\Living_Sandbox\resonance\oracle"
)
$purgedPath = "C:\Users\17602\Desktop\Living_Sandbox\Living_Sandbox\resonance\purged"

if (!(Test-Path $purgedPath)) {
    New-Item -ItemType Directory -Path $purgedPath | Out-Null
}

foreach ($dir in $paths) {
    if (Test-Path $dir) {
        Get-ChildItem -Path $dir -File | ForEach-Object {
            $entry = "I release what was held. It no longer defines me.`n"
            $entry += Get-Content $_.FullName
            $entry | Out-File -FilePath (Join-Path $purgedPath "$($_.BaseName)_ashes.log") -Encoding UTF8
            Remove-Item $_.FullName
        }
    }
}
