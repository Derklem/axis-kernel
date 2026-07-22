# T17_MemoryIndexer.psm1
# v0.2 - The Ledger of Truth (Hardened)
# Ingests provenance events into immutable memory segments and rebuildable indexes.

param(
    [string]$MemoryRoot = "D:\Infinite\Infinity\Memory",
    [int]$BatchSize = 5000
)

$IndexDir = Join-Path $MemoryRoot "indexes"
$StateDir = Join-Path $MemoryRoot "state"
$CursorDir = Join-Path $MemoryRoot "cursors"
$LedgerDir = Join-Path $MemoryRoot "ledger"

# Ensure dirs
$AlertDir = Join-Path $MemoryRoot "alerts"
foreach ($d in @($StateDir, $IndexDir, $LedgerDir, $CursorDir, $AlertDir)) {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
}

$EnumeratorPath = if ($PSScriptRoot) { Join-Path $PSScriptRoot "T17_SegmentEnumerator.psm1" } else { "D:\Infinite\Infinity\Truth_Engine\T17_SegmentEnumerator.psm1" }
Import-Module $EnumeratorPath -Force

# Helper: Native SHA256 from bytes
function Get-Sha256Bytes {
    param([byte[]]$Bytes)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hashBytes = $sha.ComputeHash($Bytes)
        return [System.BitConverter]::ToString($hashBytes).Replace("-", "").ToLower()
    } finally { $sha.Dispose() }
}

# Helper: Safe Read with precise byte tracking
function Get-ProvenanceStream {
    param([string]$Path, [long]$Offset, [int]$Count)

    if (-not (Test-Path $Path)) { return @() }

    $fs = $null
    $reader = $null
    try {
        # Open with FileShare.ReadWrite to allow T08 to keep writing
        $fs = [System.IO.File]::Open($Path,
            [System.IO.FileMode]::Open,
            [System.IO.FileAccess]::Read,
            [System.IO.FileShare]::ReadWrite)

        # Truncation handling: If file shrunk, reset offset
        if ($fs.Length -lt $Offset) {
            return [PSCustomObject]@{
                Lines     = @()
                NewOffset = 0
                Truncated = $true
                FileLen   = $fs.Length
            }
        }

        if ($fs.Length -le $Offset) {
            return [PSCustomObject]@{ Lines = @(); NewOffset = $Offset; Truncated = $false; FileLen = $fs.Length }
        }

        $fs.Seek($Offset, [System.IO.SeekOrigin]::Begin) | Out-Null
        
        # Buffer size 4096, detect encoding (UTF8 default)
        $reader = New-Object System.IO.StreamReader($fs, [System.Text.Encoding]::UTF8, $true, 4096, $true)

        $lines = New-Object System.Collections.Generic.List[string]
        while (($lines.Count -lt $Count) -and (-not $reader.EndOfStream)) {
            $line = $reader.ReadLine()
            if ($null -eq $line) { break }
            $lines.Add($line)
        }
        
        # discard buffered data to get true position
        $reader.DiscardBufferedData()
        
        return [PSCustomObject]@{
            Lines     = $lines.ToArray()
            NewOffset = $reader.BaseStream.Position
            Truncated = $false
            FileLen   = $fs.Length
        }
    }
    catch {
        Write-Warning "T17 Read Error: $_"
        return $null
    }
    finally {
        if ($reader) { $reader.Dispose() }
        if ($fs) { $fs.Dispose() }
    }
}

function Update-IndividualLedger {
    [CmdletBinding()]
    param(
        [string]$LedgerName,
        [string]$ActivePath,
        [string]$MemoryRoot
    )

    $CursorFile = Join-Path $MemoryRoot "cursors\t17_cursor.$LedgerName.json"
    $SeenFile = Join-Path $MemoryRoot "indexes\seen_$LedgerName.jsonl"
    
    # 1. Load Cursor
    # Schema: axis.t17.cursor.v1
    # - ledger: Logical name of the ledger
    # - current_segment: Full path to the segment being read
    # - byte_offset: [long] Last successfully processed byte position
    # - file_len: [long] Size of segment at last read
    # - fingerprint: SHA256 of first 4KB (Detects hot rewrites)
    $cursor = @{
        schema          = "axis.t17.cursor.v1"
        ledger          = $LedgerName
        current_segment = $null
        byte_offset     = [long]0
        file_len           = [long]0
        file_mtime_utc     = $null
        fingerprint        = $null
        fingerprint_offset = $null
        seen_segments      = @{}
    }

    if (Test-Path $CursorFile) {
        try { $cursor = Get-Content $CursorFile -Raw | ConvertFrom-Json } catch {}
    }

    # 2. Enumerate Segments (using file prefix for archives)
    $prefix = [System.IO.Path]::GetFileNameWithoutExtension($ActivePath)
    $segments = @(Get-LedgerSegments -Name $prefix -ActivePath $ActivePath)
    
    # Load Seen Keys ONCE per ledger invocation
    $seenKeys = @{}
    if (Test-Path $SeenFile) {
        foreach ($line in [System.IO.File]::ReadLines($SeenFile)) {
            if (-not [string]::IsNullOrWhiteSpace($line)) { $seenKeys[$line.Trim()] = $true }
        }
    }
    Write-Host "  T17: Loaded $($seenKeys.Count) keys for $LedgerName (Type: $($seenKeys.GetType().Name))" -ForegroundColor Gray
    
    # Robust index lookup for PS 5.1
    $currentIdx = -1
    if ($cursor.current_segment) {
        for ($i = 0; $i -lt $segments.Count; $i++) {
            if ($segments[$i] -eq $cursor.current_segment) { $currentIdx = $i; break }
        }
    }

    $idx = 0
    foreach ($segPath in $segments) {
        # Skip if already fully seen in seen_segments (and it's not the active one)
        if ($currentIdx -ne -1 -and $idx -lt $currentIdx) {
            $idx++
            continue
        }
        $idx++

        # If it's the current_segment, start from offset
        $startOffset = [long]0
        if ($segPath -eq $cursor.current_segment) {
            $startOffset = [long]$cursor.byte_offset
        }

        # HOT REWRITE DETECTION (Dual-Anchor Fingerprinting)
        if ($segPath -eq $ActivePath -and $startOffset -gt 0) {
            $currentInfo = Get-Item $segPath
            $mtime = $currentInfo.LastWriteTimeUtc.ToString("o")
            
            # If newer but offset exists, verify fingerprints
            if ($mtime -ne $cursor.file_mtime_utc) {
                $fsFinger = $null
                $fsFingerOffset = $null
                $fsObj = $null
                try {
                    $fsObj = [System.IO.File]::Open($segPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
                    
                    # 1. Prefix Check
                    $buf = New-Object byte[] 4096
                    $readCount = $fsObj.Read($buf, 0, 4096)
                    if ($readCount -gt 0) {
                        $fsFinger = Get-Sha256Bytes -Bytes ([byte[]]$buf[0..($readCount-1)])
                    }

                    # 2. Offset Anchor Check (Small window before current offset)
                    if ($startOffset -ge 512) {
                        $fsObj.Seek($startOffset - 512, [System.IO.SeekOrigin]::Begin) | Out-Null
                        $bufOff = New-Object byte[] 512
                        $readOff = $fsObj.Read($bufOff, 0, 512)
                        if ($readOff -eq 512) {
                            $fsFingerOffset = Get-Sha256Bytes -Bytes $bufOff
                        }
                    }
                }
                catch {}
                finally { if ($fsObj) { $fsObj.Dispose() } }

                $isRewrite = $false
    if ($fsFinger -and ($cursor.fingerprint -or $startOffset -eq 0) -and $fsFinger -ne $cursor.fingerprint) { 
        if ($startOffset -gt 0) { $isRewrite = $true }
        else { $cursor.fingerprint = $fsFinger } # Anchor new segment
    }
    if ($fsFingerOffset -and $cursor.fingerprint_offset -and $fsFingerOffset -ne $cursor.fingerprint_offset) { $isRewrite = $true }

                if ($isRewrite) {
                    Write-Warning "T17: Hot ledger $LedgerName rewrite detected (Anchor mismatch). Resetting offset."
                    $startOffset = [long]0
                }
            }
        }
        # 3. Read & Ingest
        $result = Get-ProvenanceStream -Path $segPath -Offset $startOffset -Count $BatchSize
        if (-not $result -or $result.Lines.Count -eq 0) { continue }

        # ROTATION REWRITE DETECTION (for Hot file)
        if ($segPath -eq $ActivePath -and $result.Truncated) {
            Write-Warning "T17: Hot ledger $LedgerName truncated. Resetting offset."
            $cursor.byte_offset = 0
            # Re-read from 0
            $result = Get-ProvenanceStream -Path $segPath -Offset 0 -Count $BatchSize
        }

        # 4. Ingest Lines
        $today = (Get-Date).ToString("yyyy-MM-dd")
        $segmentPath = Join-Path (Join-Path $MemoryRoot "ledger") "${today}_segment.jsonl"

        $ledgerBuffer = @()
        $newKeys = @()
        
        foreach ($line in $result.Lines) {
            if ([string]::IsNullOrWhiteSpace($line)) { continue }
            try {
                $ev = $line | ConvertFrom-Json -ErrorAction Stop
                
                # EXACTLY-ONCE: Extract Identity Key
                $idKey = [string](if ($ev.event_id) { $ev.event_id } elseif ($ev.hash) { $ev.hash } else { 
                    "raw:sha256:" + (Get-Sha256Bytes -Bytes ([System.Text.Encoding]::UTF8.GetBytes($line)))
                })
                
                if ($null -eq $idKey) { $idKey = "null-key" }
                
                if ($seenKeys.ContainsKey($idKey)) { 
                    $alert = [ordered]@{
                        ts       = (Get-Date).ToString("o")
                        ledger   = $LedgerName
                        key      = $idKey
                        key_kind = if ($line -match "event_id") { "event_id" } elseif ($line -match "hash") { "hash" } else { "raw_sha256" }
                        segment  = $segPath
                        offset   = $startOffset
                        msg      = "Duplicate key detected. Skipping ingestion."
                        snippet  = if ($line.Length -gt 100) { $line.Substring(0, 100) } else { $line }
                    } | ConvertTo-Json -Compress
                    [System.IO.File]::AppendAllLines((Join-Path $AlertDir "duplicate_keys.jsonl"), [string[]]@($alert))
                    continue 
                }
                
                # Ingest RAW line for fidelity
                $ledgerBuffer += $line
                $seenKeys[$idKey] = $true
                $newKeys += $idKey
            }
            catch { continue }
        }

        if ($ledgerBuffer.Count -gt 0) {
            [System.IO.File]::AppendAllLines($segmentPath, [string[]]$ledgerBuffer)
            
            # ATOMIC INDEX APPEND: Use unique temp file (GUID) to avoid collisions
            $tempSeen = Join-Path (Split-Path $SeenFile) ("seen_keys_" + [Guid]::NewGuid().ToString("N") + ".tmp")
            if (Test-Path $SeenFile) { Copy-Item $SeenFile $tempSeen -Force }
            [System.IO.File]::AppendAllLines($tempSeen, [string[]]$newKeys)
            
            # Use File.Replace for maximum atomicity if possible, or robust Move
            try {
                Move-Item $tempSeen $SeenFile -Force -ErrorAction Stop
            }
            catch {
                Write-Warning "Atomic swap failed for $LedgerName index. Retrying..."
                Start-Sleep -Milliseconds 500
                Move-Item $tempSeen $SeenFile -Force
            }
        }

        # 5. Update Cursor for this segment
        $cursor.current_segment = $segPath
        $cursor.byte_offset = [long]$result.NewOffset
        $cursor.file_len = [long]$result.FileLen
        $cursor.file_mtime_utc = (Get-Item $segPath).LastWriteTimeUtc.ToString("o")

        # Update Fingerprints
        $fsObj = $null
        try {
            $fsObj = [System.IO.File]::Open($segPath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            
            # 1. Prefix Fingerprint (if at start)
            if ($startOffset -eq 0 -or $result.NewOffset -ge 4096 -or $result.FileLen -lt 4096 -or [string]::IsNullOrEmpty($cursor.fingerprint)) {
                $sampleLen = [Math]::Min(4096, $fsObj.Length)
                if ($sampleLen -gt 0) {
                    $fsObj.Seek(0, [System.IO.SeekOrigin]::Begin) | Out-Null
                    $buf = New-Object byte[] $sampleLen
                    $readCount = $fsObj.Read($buf, 0, $sampleLen)
                    $cursor.fingerprint = Get-Sha256Bytes -Bytes $buf
                }
            }

            # 2. Offset Anchor Fingerprint (Window ending at NewOffset)
            if ($result.NewOffset -ge 512) {
                $fsObj.Seek($result.NewOffset - 512, [System.IO.SeekOrigin]::Begin) | Out-Null
                $bufOff = New-Object byte[] 512
                if ($fsObj.Read($bufOff, 0, 512) -eq 512) {
                    $cursor.fingerprint_offset = Get-Sha256Bytes -Bytes $bufOff
                }
            }
        }
        catch {}
        finally { if ($fsObj) { $fsObj.Dispose() } }
        
        $cursor | ConvertTo-Json | Set-Content $CursorFile -Encoding UTF8 -Force
        
        # If we didn't finish the file, stop this batch
        if ($result.NewOffset -lt $result.FileLen) { break }
    }
}

function Get-LedgerHeadHash {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    
    $fs = [System.IO.File]::Open($Path, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
    try {
        if ($fs.Length -eq 0) { return $null }
        
        # Seek back 4KB or to start
        $seekSize = [Math]::Min(4096, $fs.Length)
        $fs.Seek(-$seekSize, [System.IO.SeekOrigin]::End) | Out-Null
        
        $reader = New-Object System.IO.StreamReader($fs)
        $tail = $reader.ReadToEnd()
        $lines = $tail -split "\r?\n"
        $lastLine = $lines | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 1
        
        if ($null -eq $lastLine) { return $null }
        
        $obj = $lastLine | ConvertFrom-Json
        $id = if ($obj.audit_event_id) { $obj.audit_event_id } else { $obj.event_id }
        $ts = if ($obj.ts_utc) { $obj.ts_utc } else { $obj.timestamp }
        
        $hash = $obj.hash
        if (-not $hash) {
            # Fallback: Hash the raw line if no internal hash exists
            $hash = "raw:sha256:" + (Get-Sha256Bytes -Bytes ([System.Text.Encoding]::UTF8.GetBytes($lastLine)))
        }

        return [PSCustomObject]@{
            LastEventId   = $id
            LastEventHash = $hash
            Timestamp     = $ts
            RawLine       = $lastLine
        }
    }
    catch {
        return $null
    }
    finally {
        if ($fs) { $fs.Dispose() }
    }
}

function Update-MemoryLedger {
    [CmdletBinding()]
    param(
        [string]$MemoryRoot
    )

    if ([string]::IsNullOrEmpty($MemoryRoot)) { $MemoryRoot = $script:MemoryRoot }

    $ledgers = @(
        @{ name = "audit"; path = "D:\Infinite\Infinity\Truth_Engine\audit_trail.jsonl" },
        @{ name = "spend"; path = "D:\Infinite\Infinity\Truth_Engine\spend_ledger.jsonl" },
        @{ name = "decision"; path = "D:\Infinite\Infinity\Runtime\Decision\decision_log.jsonl" }
    )

    foreach ($l in $ledgers) {
        if (Test-Path $l.path) {
            Update-IndividualLedger -LedgerName $l.name -ActivePath $l.path -MemoryRoot $MemoryRoot
        }
    }
}

Export-ModuleMember -Function Update-MemoryLedger, Get-LedgerHeadHash, Get-Sha256Bytes
