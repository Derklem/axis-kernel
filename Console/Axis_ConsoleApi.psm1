# Axis_ConsoleApi.psm1
# Phase 50: Read-Only Data Access Layer for Forensics Console

$Root = "D:\Infinite\Infinity"
$GovDir = Join-Path $Root "Governance"
$TruthDir = Join-Path $Root "Truth_Engine"
$MemoryDir = Join-Path $Root "Memory"
$PackDir = Join-Path $MemoryDir "packs"
$AlertsDir = Join-Path $MemoryDir "alerts"

function Get-AxisSafeTail {
    param($path, $count)
    if (-not (Test-Path $path)) { return @() }
    
    $content = Get-Content $path -Tail $count -ErrorAction SilentlyContinue 
    if (-not $content) { return @() }
    
    $results = @()
    foreach ($line in $content) {
        try {
            if (-not [string]::IsNullOrWhiteSpace($line)) {
                $results += ($line | ConvertFrom-Json)
            }
        } catch { }
    }
    return $results
}

function Get-FirstOrNull($arr) {
    if ($null -eq $arr) { return $null }
    if ($arr -is [System.Collections.IEnumerable] -and -not ($arr -is [string])) {
        return ($arr | Select-Object -First 1)
    }
    return $arr
}

function Get-ConsoleStatus {
    $pulseArr = Get-AxisSafeTail (Join-Path $GovDir "integrity_pulse_ledger.jsonl") 1
    $anchorArr = Get-AxisSafeTail (Join-Path $GovDir "external_anchor_ledger.jsonl") 1
    $compArr = Get-AxisSafeTail (Join-Path $PackDir "compaction_manifest.jsonl") 1
    
    $pulse = Get-FirstOrNull $pulseArr
    $anchor = Get-FirstOrNull $anchorArr
    $compaction = Get-FirstOrNull $compArr
    
    # Get last 5 alerts
    $alerts = @()
    if (Test-Path $AlertsDir) {
        $alertFiles = Get-ChildItem $AlertsDir -Filter "*.jsonl" | Sort-Object LastWriteTime -Descending | Select-Object -First 5
        if ($alertFiles) {
            foreach ($f in $alertFiles) {
                # Ensure we pass full path
                $a = Get-AxisSafeTail $f.FullName 1
                if ($a) { $alerts += $a }
            }
        }
    }
    
    # Normalize Alerts
    $alertsNorm = @()
    foreach ($a in $alerts) {
        $ts = if ($a.ts) { $a.ts } elseif ($a.timestamp) { $a.timestamp } else { $a.ts_utc }
        $comp = if ($a.component) { $a.component } elseif ($a.ledger) { $a.ledger } else { "System" }
        $code = if ($a.result_code) { $a.result_code } elseif ($a.msg) { $a.msg } else { "ALERT" }
        
        $alertsNorm += @{
            ts = $ts
            component = $comp
            result_code = $code
        }
    }

    $status = @{
        ts_utc = (Get-Date).ToString("o")
        pulse = $pulse
        anchor = $anchor
        compaction = $compaction
        alerts = $alertsNorm
        
        # System Vitals (Added for Phase 61)
        # Normalized for Experience Layer Stability
        ProcessId = $PID
        WorkingSet64 = [System.Diagnostics.Process]::GetCurrentProcess().WorkingSet64
        HandleCount = [System.Diagnostics.Process]::GetCurrentProcess().HandleCount
        
        # Explicit Aliases for Client Compatibility
        pid = $PID
        ws_mb = [math]::Round([System.Diagnostics.Process]::GetCurrentProcess().WorkingSet64 / 1MB, 2)
        handles = [System.Diagnostics.Process]::GetCurrentProcess().HandleCount
    }
    return $status
}

function Find-AxisRecord {
    param([string]$Key)
    
    if ([string]::IsNullOrWhiteSpace($Key)) { return $null }
    
    # 1. Check Hot Segments (Memory/ledger/*_segment.jsonl)
    $hotSegments = Get-ChildItem (Join-Path $MemoryDir "ledger") -Filter "*_segment.jsonl" | Sort-Object Name -Descending
    foreach ($seg in $hotSegments) {
        $found = Select-String -Path $seg.FullName -Pattern $Key -SimpleMatch -List
        if ($found) {
            $line = $found.Line
            $rec = $(try { $line | ConvertFrom-Json } catch { $null })
            return @{
                found = $true
                key = $Key
                source = @{ tier="hot"; file=$seg.Name; line=$found.LineNumber }
                record = $rec
                raw = $line
            }
        }
    }
    
    # 2. Check Warm Indexes (Memory/packs/*_pack.index.jsonl)
    $indexes = Get-ChildItem $PackDir -Filter "*_pack.index.jsonl" | Sort-Object Name -Descending
    $useFastContains = ($Key.Length -ge 8)

    foreach ($idx in $indexes) {
        # Stream read index for speed
        $reader = [System.IO.File]::OpenText($idx.FullName)
        try {
            while (($line = $reader.ReadLine()) -ne $null) {
                if ($useFastContains -and -not $line.Contains($Key)) { continue } # Fast check
                
                try { $obj = $line | ConvertFrom-Json } catch { continue }
                if ($obj.k -eq $Key) {
                    # Found in index! Now fetch from pack.
                    $packName = $obj.pack
                    $packPath = Join-Path $PackDir $packName
                    
                    if (-not (Test-Path $packPath)) {
                        return @{ found=$false; key=$Key; message="Index hit but pack missing: $packName" }
                    }

                    $targetLine = [int]$obj.line
                    if ($targetLine -lt 1) {
                         return @{ found=$false; key=$Key; message="Index hit but invalid line: $($obj.line)" }
                    }
                    
                    # Read specific line from pack (1-based index)
                    $packLine = ""
                    $pReader = [System.IO.File]::OpenText($packPath)
                    try {
                        for ($i=1; $i -lt $targetLine; $i++) { [void]$pReader.ReadLine() }
                        $packLine = $pReader.ReadLine()
                    } finally {
                        $pReader.Dispose()
                    }
                    
                    return @{
                        found = $true
                        key = $Key
                        source = @{ tier="warm"; pack=$packName; line=$targetLine; kind=$obj.kind }
                        record = $(try { $packLine | ConvertFrom-Json } catch { $null })
                        raw = $packLine
                    }
                }
            }
        } finally {
            $reader.Dispose()
        }
    }
    
    return @{ found=$false; key=$Key; message="Not found in Hot or Warm storage." }
}

function Get-PulseHistory {
    param([int]$Count=50)
    return Get-AxisSafeTail (Join-Path $GovDir "integrity_pulse_ledger.jsonl") $Count | Sort-Object ts_utc -Descending
}

function Get-AnchorHistory {
    param([int]$Count=50)
    return Get-AxisSafeTail (Join-Path $GovDir "external_anchor_ledger.jsonl") $Count | Sort-Object timestamp -Descending
}

function Get-WarmStorageReport {
    $scriptPath = Join-Path $GovDir "Axis_Verify_WarmStorage.ps1"
    if (-not (Test-Path $scriptPath)) {
        return @{ status="SKIP"; message="Verifier missing"; }
    }

    $out = & $scriptPath -Root $Root -LatestOnly 2>&1
    $ok = ($LASTEXITCODE -eq 0)

    return @{
        status = if ($ok) { "PASS" } else { "FAIL" }
        exit_code = $LASTEXITCODE
        output = ($out | ForEach-Object { "$_" })
    }
}

Export-ModuleMember -Function Get-ConsoleStatus, Find-AxisRecord, Get-PulseHistory, Get-AnchorHistory, Get-WarmStorageReport
