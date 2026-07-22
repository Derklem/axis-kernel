# === Echo Trigger Agent ===
$sigilLog = "E:\Halcyon_Logics\sigil_log\sigil_tether_$(Get-Date -Format 'yyyyMMdd').log"
$tremorLog = "E:\Halcyon_Logics\echo_tremor.log"
$triggerLog = "E:\Halcyon_Logics\echo_trigger.log"

if (-not (Test-Path $triggerLog)) {
    New-Item -ItemType File -Path $triggerLog | Out-Null
}

$lastSigilHash = ""
$lastTremorCount = 0

while ($true) {
    $sigilLine = Get-Content $sigilLog -Tail 1
    $tremorLine = Get-Content $tremorLog -Tail 1

    $currentHash = if ($sigilLine -match "\| ([A-F0-9]{64})$") { $matches[1] } else { "" }
    $currentCount = if ($tremorLine -match "change: ([+-]?\d+)") { [int]$matches[1] } else { 0 }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    if ($currentHash -ne $lastSigilHash -and $currentCount -ne $lastTremorCount) {
        $triggerEvent = @"
[TRIGGERED ECHO] $timestamp
New Sigil Hash: $currentHash
File Count Change: $currentCount
Reason: Synchronous resonance detected.
---
"@
        Add-Content -Path $triggerLog -Value $triggerEvent
        $lastSigilHash = $currentHash
        $lastTremorCount = $currentCount
    }

    Start-Sleep -Seconds 150
}
