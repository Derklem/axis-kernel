
function Measure-TransportState {
    param(
        [string]$QueuePath = "D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl",
        [string]$CursorPath = "D:\Infinite\Infinity\Runtime\Decision\queue_cursor.json",
        [string]$StatePath = "D:\Infinite\Infinity\Runtime\Decision\transport_state.json"
    )

    $metrics = [ordered]@{
        ts_utc = (Get-Date).ToUniversalTime().ToString("o")
        queue_depth_lines = 0
        byte_lag = 0
        latency_ms = 0
        status = "HEALTHY"
    }

    if (-not (Test-Path $QueuePath)) {
        $metrics.status = "NO_QUEUE"
        $metrics | ConvertTo-Json | Set-Content $StatePath -Force
        return $metrics
    }

    # 1. Get Physical Queue State
    try {
        $qItem = Get-Item $QueuePath
        $qLen = $qItem.Length
    } catch {
        $metrics.status = "QUEUE_ACCESS_ERROR"
        $metrics | ConvertTo-Json | Set-Content $StatePath -Force
        return $metrics
    }

    # 2. Get Cursor State
    $cBytes = 0
    if (Test-Path $CursorPath) {
        try {
            $cursor = Get-Content $CursorPath -Raw | ConvertFrom-Json
            $cBytes = $cursor.byte_offset
        } catch {
            Write-Warning "Failed to read cursor: $_"
        }
    }

    # 3. Calculate Lag
    $metrics.byte_lag = $qLen - $cBytes
    if ($metrics.byte_lag -lt 0) { 
        # Truncation or reset detected
        $metrics.byte_lag = $qLen 
        $cBytes = 0 # Assume we need to read from start if confused
    }

    # 4. Measure Detail (Depth & Latency)
    # Only read file if there is lag
    if ($metrics.byte_lag -gt 0) {
        $fs = $null
        $reader = $null
        try {
            $fs = [System.IO.File]::Open($QueuePath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
            
            if ($cBytes -lt $fs.Length) {
                # Seek to cursor
                $fs.Seek($cBytes, [System.IO.SeekOrigin]::Begin) | Out-Null
                $reader = [System.IO.StreamReader]::new($fs)
                
                $pendingLines = 0
                $firstItemTs = $null
                
                while (-not $reader.EndOfStream) {
                    $line = $reader.ReadLine()
                    if (-not [string]::IsNullOrWhiteSpace($line)) {
                        $pendingLines++
                        
                        # Grab stats from the HEAD of the pending queue (oldest item)
                        if ($null -eq $firstItemTs) {
                            try {
                                $obj = $line | ConvertFrom-Json
                                
                                # Priority: Envelope TS > Intent JSON > Intent Object
                                if ($obj.ts_utc) { 
                                    $firstItemTs = [DateTime]::Parse($obj.ts_utc) 
                                } elseif ($obj.intent_json) {
                                     try {
                                        # Try to peel inner intent_json to get TS
                                        $innerInfo = $obj.intent_json | ConvertFrom-Json
                                        if ($innerInfo.ts) { $firstItemTs = [DateTime]::Parse($innerInfo.ts) }
                                     } catch {}
                                } elseif ($obj.intent -and $obj.intent.ts) {
                                    $firstItemTs = [DateTime]::Parse($obj.intent.ts)
                                }
                            } catch { 
                                # Parse error ignored for metrics
                            }
                        }
                    }
                }
                
                $metrics.queue_depth_lines = $pendingLines
                
                if ($null -ne $firstItemTs) {
                    $now = (Get-Date).ToUniversalTime()
                    $metrics.latency_ms = [Math]::Round(($now - $firstItemTs).TotalMilliseconds, 2)
                }
            }
        } catch {
            $metrics.status = "READ_ERROR: $_"
        } finally {
            if ($reader) { $reader.Dispose() }
            if ($fs) { $fs.Dispose() }
        }
    }

    # 5. Determine Health Status
    if ($metrics.queue_depth_lines -gt 50) {
        $metrics.status = "CRITICAL_PRESSURE"
    } elseif ($metrics.queue_depth_lines -gt 10) {
        $metrics.status = "HIGH_PRESSURE"
    } elseif ($metrics.latency_ms -gt 5000) { # 5s latency
        $metrics.status = "HIGH_LATENCY"
    }

    # 6. Publish
    $metrics | ConvertTo-Json | Set-Content $StatePath -Encoding UTF8 -Force
    
    return $metrics
}

Export-ModuleMember -Function Measure-TransportState
