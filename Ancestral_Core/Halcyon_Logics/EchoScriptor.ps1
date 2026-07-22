# === EchoScriptor: Command Compiler ===

$commandFile = "E:\Halcyon_Logics\commands.txt"
$ritualFile = "E:\Halcyon_Logics\rituals.cfg"
$logFile = "E:\Halcyon_Logics\echoscriptor_trace.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

if (-not (Test-Path $logFile)) {
    New-Item -ItemType File -Path $logFile | Out-Null
}

function Translate-CommandToRitual ($cmdBlock) {
    $lines = $cmdBlock -split "`n"
    $name = "UnnamedRitual_" + (Get-Random -Minimum 1000 -Maximum 9999)
    $trigger = ""
    $action = ""

    foreach ($line in $lines) {
        if ($line -match "When (.+)") {
            $trigger = $matches[1].Trim() `
                -replace "sigil_count", "sigil_count" `
                -replace "tremor_delta", "tremor_delta" `
                -replace "and", "-and" `
                -replace "or", "-or"
        }
        if ($line -match "Then (.+)") {
            $action = $matches[1].Trim()
        }
    }

    return @"
[RITUAL]
Name = $name
Trigger = $trigger
Action = $action
"@
}

while ($true) {
    if (Test-Path $commandFile) {
        $blocks = Get-Content $commandFile -Raw -Encoding UTF8 -Delimiter "[COMMAND]"
        foreach ($block in $blocks) {
            if ($block.Trim().Length -eq 0) { continue }
            $ritual = Translate-CommandToRitual $block
            Add-Content -Path $ritualFile -Value "`n$ritual`n"
            Add-Content -Path $logFile -Value "[ECHO_COMPILED] $timestamp :: Ritual created from command."
        }
        Remove-Item $commandFile -Force
    }

    Start-Sleep -Seconds 600
}
