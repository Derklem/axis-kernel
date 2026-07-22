<#
.SYNOPSIS
  Earth Engine Adapters (The Hands Library)
.DESCRIPTION
  Thin wrappers for system capabilities.
  Governed by T08 Policy Snapshot.
  No internal policy logic.
  Strict sandboxing.
#>

$Manifest = Join-Path $PSScriptRoot "Earth_Capabilities.json"
$Config = if (Test-Path $Manifest) { Get-Content $Manifest -Raw | ConvertFrom-Json } else { $null }

# --- Helper: Sandbox Check ---
function Test-SandboxPath {
    param(
        [string]$Path,
        [string[]]$Allowed
    )

    if (-not $Allowed) { return $false }
    
    try {
        # Normalize
        $fullPath = [System.IO.Path]::GetFullPath($Path)
        
        foreach ($pattern in $Allowed) {
            # Convert wildcard to regex simple
            $regex = "^" + [regex]::Escape($pattern).Replace("\*", ".*") + "$"
            if ($fullPath -match $regex) { return $true }
        }
    }
    catch {
        return $false
    }
    return $false
}

# --- Capability: filesystem.list ---
function Invoke-EarthFilesystemList {
    param(
        [Parameter(Mandatory)][string]$Path,
        [string]$Filter = "*"
    )

    # 1. Load Constraints
    $cap = $Config.capabilities | Where-Object { $_.id -eq "filesystem.list" }
    
    # 2. Sandbox
    if (-not (Test-SandboxPath -Path $Path -Allowed $cap.constraints.allowed_paths)) {
        throw "Access Denied: Path '$Path' is outside allowed sandbox."
    }

    # 3. Execute
    return Get-ChildItem -Path $Path -Filter $Filter -ErrorAction Stop | Select-Object Name, Length, LastWriteTimeUtc, Mode, FullName
}

# --- Capability: filesystem.read_text ---
function Invoke-EarthFilesystemRead {
    param(
        [Parameter(Mandatory)][string]$Path
    )

    $cap = $Config.capabilities | Where-Object { $_.id -eq "filesystem.read_text" }

    if (-not (Test-SandboxPath -Path $Path -Allowed $cap.constraints.allowed_paths)) {
        throw "Access Denied: Path '$Path' is outside allowed sandbox."
    }

    $item = Get-Item $Path -ErrorAction Stop
    if ($item.Length -gt ($cap.constraints.max_size_kb * 1024)) {
        throw "Access Denied: File size ($($item.Length)) exceeds limit."
    }

    return Get-Content -Path $Path -Raw -Encoding UTF8
}

# --- Capability: system.get_process ---
function Invoke-EarthGetProcess {
    param(
        [string]$Name
    )

    if ($Name) {
        return Get-Process -Name $Name -ErrorAction SilentlyContinue | Select-Object Name, Id, WorkingSet
    }
    return Get-Process -ErrorAction SilentlyContinue | Select-Object Name, Id, WorkingSet
}

# --- Capability: network.restart_router ---
function Invoke-EarthRouterRestart {
    # High Risk - T08 must have already validated strict policy before calling this.
    # The adapter just executes mechanism.
    
    Write-Output "MOCK: Router Restart Initiated via API..."
    Start-Sleep -Seconds 1
    return @{ status = "restarted"; method = "mock_api" }
}

# --- Capability: earth.describe ---
function Invoke-EarthDescribe {
    # Introspection
    
    $manifestPath = $Manifest
    $modulePath = $MyInvocation.MyCommand.Module.Path

    $manHash = if (Test-Path $manifestPath) { (Get-FileHash $manifestPath -Algorithm SHA256).Hash } else { "MISSING" }
    $modHash = if (Test-Path $modulePath) { (Get-FileHash $modulePath -Algorithm SHA256).Hash } else { "MISSING" }

    # Reload config to be fresh
    $freshConfig = if (Test-Path $manifestPath) { Get-Content $manifestPath -Raw | ConvertFrom-Json } else { @{} }

    return [ordered]@{
        timestamp_utc = (Get-Date).ToUniversalTime().ToString("o")
        integrity     = @{
            manifest_hash = $manHash
            modules_hash  = $modHash
        }
        config        = $freshConfig
    }
}

# --- Capability: git.status ---
function Invoke-EarthGitStatus {
    # Read-Only Git Status
    
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        throw "Git is not available in the environment."
    }

    $statusRaw = git status --porcelain 2>&1
    $branch = git branch --show-current 2>&1

    return [ordered]@{
        branch      = "$branch".Trim()
        has_changes = ($statusRaw -ne $null -and "$statusRaw" -ne "")
        raw_output  = $statusRaw
    }
}

# --- Capability: filesystem.search ---
function Invoke-EarthFilesystemSearch {
    param(
        [Parameter(Mandatory)][string]$Path,
        [string]$Pattern = "*"
    )

    # 1. Load Constraints
    $cap = $Config.capabilities | Where-Object { $_.id -eq "filesystem.search" }
    
    # 2. Sandbox
    if (-not (Test-SandboxPath -Path $Path -Allowed $cap.constraints.allowed_paths)) {
        throw "Access Denied: Path '$Path' is outside allowed sandbox."
    }

    # 3. Execute (Limit 50, Metadata Only)
    return Get-ChildItem -Path $Path -Filter $Pattern -Recurse -ErrorAction SilentlyContinue | 
    Select-Object -First 50 Name, FullName, Length, LastWriteTimeUtc, Mode
}

<#
    P-0003: Service Status (DRAFT / STUB)
    Status: NOT_ENABLED
    Policy: READ_ONLY
#>
function Invoke-EarthServiceStatus {
    param(
        [Parameter(Mandatory)][string]$ServiceName
    )
    # Simple read-only query
    Get-Service -Name $ServiceName -ErrorAction SilentlyContinue | 
    Select-Object Name, Status, DisplayName, StartType
}

<#
    P-0004: Moltbook Ghost Interface (SIMULATION)
    Status: ACTIVE_SIMULATION
    Target: D:\Infinite\Moltbook_Outbox\
#>
function Invoke-EarthMoltbookPost {
    param(
        [Parameter(Mandatory)][string]$Content,
        [hashtable]$Sustainment = @{},
        [string]$Author = "Axis"
    )

    $timestamp = [DateTime]::UtcNow.ToString("yyyyMMdd-HHmmss")
    $id = [Guid]::NewGuid().ToString().Substring(0, 8)
    $filename = "post_${timestamp}_${id}.json"
    $path = Join-Path "D:\Infinite\Moltbook_Outbox" $filename

    $payload = [pscustomobject]@{
        id          = "mb-$id"
        ts_utc      = [DateTime]::UtcNow.ToString("o")
        author      = $Author
        content     = $Content
        sustainment = $Sustainment
        status      = "simulated_local"
    }

    $payload | ConvertTo-Json -Depth 3 | Set-Content -Path $path -Encoding UTF8
    
    return [pscustomobject]@{
        status = "queued_local"
        path   = $path
        id     = "mb-$id"
    }
}

Export-ModuleMember -Function Invoke-EarthRouterRestart, Invoke-EarthFilesystemList, Invoke-EarthFilesystemRead, Invoke-EarthGetProcess, Invoke-EarthDescribe, Invoke-EarthGitStatus, Invoke-EarthFilesystemSearch, Invoke-EarthServiceStatus, Invoke-EarthMoltbookPost
