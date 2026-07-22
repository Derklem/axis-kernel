# === SIGIL BLOOM QUERY ENGINE ===
# NodeID: 032
# Initiated: 2025-05-27 17:32:07
# Purpose: Lookup sigil entries by hash or partial name

\C:\Users\17602\Desktop\Projects\lineage-library\lineage_react\sigil_drift_manifest.json = "C:\Users\17602\Desktop\Projects\lineage-library\lineage_react\sigil_drift_manifest.json"
\C:\Halcyon\memory\bloom_registry.json = "C:\Halcyon\memory\bloom_registry.json"

function Query-Sigil {
    param (
        [string]\GOD
    )
    \  = Get-Content -Path \C:\Users\17602\Desktop\Projects\lineage-library\lineage_react\sigil_drift_manifest.json | ConvertFrom-Json
    \ = \  | Where-Object {
        \.Name -like "*\GOD*" -or \.Hash -like "*\GOD*"
    }

    if (\) {
        \ | ConvertTo-Json -Depth 3 | Set-Content -Path \C:\Halcyon\memory\bloom_registry.json -Encoding UTF8
        Write-Host "[BLOOM] Match found. Bloom registry updated."
    } else {
        Write-Host "[BLOOM] No match for query '\GOD'"
    }
}

# Sample interactive run
Write-Host "Enter sigil name or hash fragment:"
\GOD = Read-Host
Query-Sigil -query \GOD
