# Axis_Log_Rotation.ps1
# Phase 42/43.2: Safely rotates ledger entries into monthly archives with continuity.

param(
    [switch]$VerifyOnly
)

$ErrorActionPreference = "Stop"

$Root = "D:\Infinite\Infinity"
$TruthDir = Join-Path $Root "Truth_Engine"
$ArchiveDir = Join-Path $TruthDir "Archive"

if (-not (Test-Path $ArchiveDir)) {
    New-Item -ItemType Directory -Path $ArchiveDir -Force | Out-Null
}

$Ledgers = @(
    @{ Name = "audit_trail"; Path = Join-Path $TruthDir "audit_trail.jsonl" },
    @{ Name = "spend_ledger"; Path = Join-Path $TruthDir "spend_ledger.jsonl" }
)

function Get-MonthKey($isoTimestamp) {
    try {
        if ([string]::IsNullOrWhiteSpace($isoTimestamp)) { return "INVALID" }
        return ([DateTime]$isoTimestamp).ToString("yyyy-MM")
    }
    catch {
        return "INVALID"
    }
}

function Get-FileTailHash($Path) {
    if (-not (Test-Path $Path)) { return $null }
    $fs = $null
    try {
        $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        if ($fs.Length -eq 0) { return $null }
        $seekSize = [Math]::Min(4096, $fs.Length)
        $fs.Seek(-$seekSize, [System.IO.SeekOrigin]::End) | Out-Null
        $reader = New-Object System.IO.StreamReader($fs)
        $tail = $reader.ReadToEnd()
        $lInTail = $tail -split "\r?\n" | Where-Object { -not [string]::IsNullOrWhiteSpace($_) }
        $lastLine = $lInTail | Select-Object -Last 1
        if ($null -eq $lastLine) { return $null }
        $obj = $lastLine | ConvertFrom-Json
        return $obj.hash
    }
    catch { return $null }
    finally { if ($fs) { $fs.Dispose() } }
}

function Rotate-Ledger($ledgerMeta) {
    $name = $ledgerMeta.Name
    $path = $ledgerMeta.Path
    
    Write-Host "Checking $name..." -ForegroundColor Cyan

    if (-not (Test-Path $path)) {
        Write-Warning "  File not found: $path"
        return
    }

    # 1. Read All Lines
    $lines = [System.IO.File]::ReadAllLines($path)
    if ($lines.Count -eq 0) { return }

    # 2. Parse and Group
    $groups = [ordered]@{}
    $currentMonth = (Get-Date).ToString("yyyy-MM")
    $parseFail = $false
    
    for ($i = 0; $i -lt $lines.Count; $i++) {
        $line = $lines[$i]
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        
        try {
            $obj = $line | ConvertFrom-Json
            $ts = if ($obj.ts_utc) { $obj.ts_utc } else { $obj.timestamp } 
            
            $mKey = Get-MonthKey $ts
            if ($mKey -eq "INVALID") { 
                Write-Warning "  Invalid timestamp at line $($i+1)"
                $parseFail = $true; break 
            }
            
            if ($groups.Keys -notcontains $mKey) {
                $groups[$mKey] = [System.Collections.ArrayList]::new()
            }
            [void]$groups[$mKey].Add($line)
        }
        catch {
            Write-Warning "  JSON Parse error at line $($i+1): $_"
            $parseFail = $true; break
        }
    }

    if ($parseFail) {
        Write-Error "  Aborting rotation for $name due to parse errors."
        return
    }

    Write-Host "  Found Month Keys: $($groups.Keys -join ', ')" -ForegroundColor Cyan

    # 3. Process Historical Groups
    $keysToArchive = $groups.Keys | Where-Object { $_ -lt $currentMonth }
    
    if ($keysToArchive.Count -eq 0) {
        Write-Host "  No historical segments found to rotate." -ForegroundColor Gray
    } else {
        $archivedKeysWritten = [System.Collections.Generic.List[string]]::new()
        $archiveTailHashes = @{}
        
        foreach ($key in $keysToArchive) {
            $archivePath = Join-Path $ArchiveDir "$name.$key.jsonl"
            $entries = $groups[$key]
            
            Write-Host "  Migrating $key ($($entries.Count) lines) -> $archivePath" -ForegroundColor Yellow
            
            if (Test-Path $archivePath) {
                Write-Warning "  Archive $archivePath already exists. Validating continuity against disk truth."
                $diskTail = Get-FileTailHash $archivePath
                if ($null -eq $diskTail) {
                    Write-Error "  [CRITICAL] Could not read valid tail hash from existing archive: $archivePath"
                    return
                }
                $archiveTailHashes[$key] = $diskTail
                [void]$archivedKeysWritten.Add($key)
                continue
            }
            
            [System.IO.File]::WriteAllLines($archivePath, [string[]]$entries.ToArray())
            
            $lastLine = $entries | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 1
            if ($lastLine) {
                $lastObj = $lastLine | ConvertFrom-Json
                $archiveTailHashes[$key] = $lastObj.hash
            }
            [void]$archivedKeysWritten.Add($key)
        }

        # 4. Chain Continuity Verification
        $remainingKeys = $groups.Keys | Where-Object { $_ -ge $currentMonth }
        if ($archivedKeysWritten.Count -gt 0 -and $remainingKeys.Count -gt 0) {
            $maxArchKey = $archivedKeysWritten | Sort-Object | Select-Object -Last 1
            $archTailHash = $archiveTailHashes[$maxArchKey]
            
            $minRemKey = $remainingKeys | Sort-Object | Select-Object -First 1
            $firstRemLine = ($groups[$minRemKey] | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -First 1)
            $firstRemObj = $firstRemLine | ConvertFrom-Json
            $hotHeadPrev = $firstRemObj.previous_hash

            if ("$hotHeadPrev" -ne "$archTailHash") {
                Write-Error "  [CRITICAL] Chain Continuity Broken! $name rotation aborted."
                Write-Error "             Archive ($maxArchKey) Tail Hash: $archTailHash"
                Write-Error "             Hot Head ($minRemKey) Prev Hash: $hotHeadPrev"
                return
            }
            Write-Host "  [PASS] Continuity Verified against ARCHIVE truth: $archTailHash" -ForegroundColor Green
        }
    }

    if ($VerifyOnly) {
        Write-Host "  [VERIFY] Continuity confirmed ($name). Skipping write." -ForegroundColor Gray
        return
    }

    # 5. Rewrite Hot Ledger
    $remainingKeys = $groups.Keys | Where-Object { $_ -ge $currentMonth }
    $newContent = [System.Collections.ArrayList]::new()
    foreach ($key in $remainingKeys) {
        $newContent.AddRange($groups[$key])
    }

    Write-Host "  Rewriting hot ledger ($($newContent.Count) lines remain)..." -ForegroundColor White
    $tempPath = $path + ".tmp"
    [System.IO.File]::WriteAllLines($tempPath, [string[]]$newContent.ToArray())
    Remove-Item $path -Force
    Move-Item $tempPath $path -Force
    
    Write-Host "  [OK] Rotation Complete for $name" -ForegroundColor Green
}

# --- Execution ---
Write-Host "--- AXIS LOG ROTATION (Phase 42) ---" -ForegroundColor Cyan
foreach ($l in $Ledgers) {
    Rotate-Ledger $l
}
