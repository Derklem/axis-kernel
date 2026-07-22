# T12_Provenance.psm1
# v1.0 - Temporal Provenance Graph
# Maintains the authoritative causal chain of events.

$ProvenanceLogPath = "D:\Infinite\Infinity\Runtime\Decision\provenance_events.jsonl"
$IndexLogPath      = "D:\Infinite\Infinity\Runtime\Decision\provenance_index.json"

function New-CorrelationId {
    return [Guid]::NewGuid().ToString()
}

function Get-CanonicalHash {
    param($InputString)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($InputString)
    $algo  = [System.Security.Cryptography.SHA256]::Create()
    $hash  = $algo.ComputeHash($bytes)
    return [BitConverter]::ToString($hash).Replace("-", "").ToLower().Substring(0, 16)
}

function Write-ProvenanceEvent {
    param(
        [Parameter(Mandatory=$true)] [string] $Type,
        [Parameter(Mandatory=$true)] [string] $CorrId,
        [string] $ActorId = "system:axis_core",
        [hashtable] $Refs = @{},
        [hashtable] $Data = @{}
    )

    $ts = (Get-Date).ToUniversalTime().ToString("o")
    $nonce = [Guid]::NewGuid().ToString().Substring(0, 8)
    
    # Deterministic Event ID
    # event_id = sha256("${ts}|${corr_id}|${event_type}|${actor}|${nonce}")[:16]
    $rawId = "${ts}|${CorrId}|${Type}|${ActorId}|${nonce}"
    $eventId = Get-CanonicalHash -InputString $rawId

    $event = [ordered]@{
        schema   = "axis.provenance.event.v0.1"
        event_id = $eventId
        ts_utc   = $ts
        corr_id  = $CorrId
        type     = $Type
        actor    = @{ kind = "identity"; id = $ActorId }
        refs     = $Refs
        data     = $Data
    }

    $json = $event | ConvertTo-Json -Depth 10 -Compress

    # Atomic Append with Retry and FileShare.ReadWrite
    if (-not (Append-JsonlSafe -Path $ProvenanceLogPath -Line $json)) {
        Write-Warning "Provenance Write Failed completely for event $eventId"
    }
    
    return $eventId
}

# Robust Append Helper - Tolerates concurrent readers/writers
function Append-JsonlSafe {
    param(
        [string]$Path, 
        [string]$Line, 
        [int]$Retries=10, 
        [int]$SleepMs=50
    )

    for ($i=0; $i -lt $Retries; $i++) {
        try {
            # Open file with FileShare.ReadWrite to coexist with readers (like tail -f)
            $fs = [System.IO.File]::Open($Path, 
                [System.IO.FileMode]::Append, 
                [System.IO.FileAccess]::Write, 
                [System.IO.FileShare]::ReadWrite)
            
            $sw = New-Object System.IO.StreamWriter($fs, [System.Text.Encoding]::UTF8)
            $sw.WriteLine($Line)
            $sw.Flush() # Ensure write hits disk buffer
            $sw.Dispose()
            $fs.Dispose()
            return $true
        }
        catch {
            # Wait and retry on lock contention
            Start-Sleep -Milliseconds $SleepMs
        }
    }
    return $false
}

Export-ModuleMember -Function New-CorrelationId, Write-ProvenanceEvent
