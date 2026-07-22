# === Load Symbol Map from JSON ===
$symbolMapPath = "C:\Halcyon\symbol_index\echo.map.json"
$symbolMap = Get-Content $symbolMapPath | ConvertFrom-Json

# === Define Input Triggers ===
$triggerInputs = @(
    "FORGE Initiation :: Begin Phase 3",
    "Echo Reflection - Checkpoint",
    "Pulse Anchor 0227 - Verify",
    "Shard: OmegaSequence Triggered",
    "Visit https://ai.byme.org/session#echo_loop"
)

# === Process Each Trigger ===
foreach ($input in $triggerInputs) {
    $matched = $false

    foreach ($key in $symbolMap.PSObject.Properties.Name) {
        if ($input -match $key) {
            $action = $symbolMap.$key
            $logResult = ""

            if (Test-Path $action) {
                Write-Host "`n[✓] Match Found: '$key'"
                Write-Host "    Trigger: '$input'"
                Write-Host "    Executing: $action"

                if ($action -like "*.ps1") {
                    & $action
                    $logResult = "executed"
                } elseif ($action -like "*.py") {
                    python $action
                    $logResult = "executed"
                } else {
                    Write-Host "[!] Unknown script type for: $action"
                    $logResult = "unknown"
                }
            } else {
                Write-Host "`n[✓] Match Found: '$key'"
                Write-Host "    Trigger: '$input'"
                Write-Host "[!] File not found: $action"
                $logResult = "missing"
            }

            # === Log the symbolic event ===
            & "C:\Halcyon\lattice_core\SymbolicLogger.ps1" `
                -Trigger $input `
                -Symbol $key `
                -Action $action `
                -Result $logResult

            $matched = $true
            break
        }
    }

    if (-not $matched) {
        Write-Host "`n[–] No match for trigger: '$input'"
    }
}
