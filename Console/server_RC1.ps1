# Console/server.ps1
# Phase 50: Lightweight, Read-Only HTTP Server for Axis Forensics Console

param([int]$Port = 8787, [switch]$LiveWrapper)

$ErrorActionPreference = "Stop"
# Start-Transcript -Path "D:\Infinite\Infinity\Console\server_transcript.log" -Force

try {
    # --- Initialization ---
    $Root = "D:\Infinite\Infinity"
    $ConsoleDir = Join-Path $Root "Console"
    $PublicDir = Join-Path $ConsoleDir "public"
    $GovDir = Join-Path $Root "Governance"
    $ModulePath = Join-Path $PSScriptRoot "Axis_ConsoleApi.psm1"
    $EconModule = Join-Path $GovDir "Economics\Axis_IntegrityEconomics.psm1"
    $SchedulerModule = Join-Path $GovDir "Witness\Scheduler\Axis_Witness_Scheduler.psm1"

    # --- Phase 60: Wrapper Guard ---
    # Prevents manual startup if a lockfile exists, unless authorized by the wrapper.
    $WrapperLock = "D:\Infinite\Infinity\Runtime\State\axis_live.lock"
    if ((Test-Path $WrapperLock) -and -not $LiveWrapper) {
        Write-Host "ERROR: server_RC1.ps1 execution is locked by Phase 60 Wrapper." -ForegroundColor Red
        Write-Host "Use 'Governance\Invoke-AxisLive.ps1' to manage this instance." -ForegroundColor Yellow
        exit 1
    }

    Write-Host "Starting Axis Console Server... (Version: RUNSPACE-RECREATED)" -ForegroundColor Cyan
    
    if (-not (Test-Path $ModulePath)) { throw "API Module not found at $ModulePath" }
    Import-Module $ModulePath -Force -ErrorAction Stop
    
    if (Test-Path $EconModule) { Import-Module $EconModule -Force -ErrorAction Stop; Write-Host "Econ Module Loaded." -ForegroundColor Green }
    else { Write-Warning "Econ Module not found at $EconModule" }

    if (Test-Path $SchedulerModule) { Import-Module $SchedulerModule -Force -ErrorAction Stop; Write-Host "Scheduler Module Loaded." -ForegroundColor Green }
    else { Write-Warning "Scheduler Module not found at $SchedulerModule" }
    
    Write-Host "Debug: Checking Provenance Module..."
    $ProvModule = Join-Path $Root "Governance\Axis_Provenance.psm1"
    Write-Host "Debug: ProvModule Path: $ProvModule"
    if (Test-Path $ProvModule) { 
        Write-Host "Debug: Importing Provenance..."
        Import-Module $ProvModule -Force -ErrorAction Stop
        Write-Host "Provenance Module Loaded." -ForegroundColor Green 
    }
    else { Write-Warning "Provenance Module not found at $ProvModule" }

    # --- Phase 67: Centralized Path Resolution ---
    $PolicyFile = Join-Path $GovDir "integrity_policy.json"
    $PulseLedger = Join-Path $GovDir "integrity_pulse_ledger.jsonl"
    $WitnessLedger = Join-Path $GovDir "Axis_Witness_Ledger.jsonl"
    $EconLedger = Join-Path $GovDir "econ_ledger.jsonl"
    $PropLedger = Join-Path $GovDir "witness_proposals.jsonl"
    $ApproveLedger = Join-Path $GovDir "witness_approvals.jsonl"

    if (Test-Path $PolicyFile) {
        try {
            $pol = Get-Content $PolicyFile -Raw | ConvertFrom-Json
            if ($pol.paths.pulse_ledger) { $PulseLedger = $pol.paths.pulse_ledger }
            if ($pol.paths.witness_ledger) { $WitnessLedger = $pol.paths.witness_ledger }
            if ($pol.paths.econ_ledger) { $EconLedger = $pol.paths.econ_ledger }
            if ($pol.paths.witness_proposals) { $PropLedger = $pol.paths.witness_proposals }
            if ($pol.paths.witness_approvals) { $ApproveLedger = $pol.paths.witness_approvals }
            
            # Phase 68: Caps
            $Global:CommitLimit_Hourly = 10
            $Global:CommitLimit_ICU_Hourly = 500
            if ($pol.limits.max_commits_per_hour) { $Global:CommitLimit_Hourly = $pol.limits.max_commits_per_hour }
            if ($pol.limits.max_commit_icu_per_hour) { $Global:CommitLimit_ICU_Hourly = $pol.limits.max_commit_icu_per_hour }
            
            Write-Host "Centralized Policy Loaded." -ForegroundColor Green
        }
        catch { Write-Warning "Policy Load Failed, using defaults." }
    }
    
    # HMAC Secret (In-memory singleton for RC1)
    $Global:ApprovalSecret = [System.Guid]::NewGuid().ToString()

    Write-Host "CANONICAL_PULSE_LEDGER=$PulseLedger" -ForegroundColor Gray
    Write-Host "CANONICAL_WITNESS_LEDGER=$WitnessLedger" -ForegroundColor Gray
    Write-Host "CANONICAL_ECON_LEDGER=$EconLedger" -ForegroundColor Gray
    Write-Host "CANONICAL_PROP_LEDGER=$PropLedger" -ForegroundColor Gray
    Write-Host "CANONICAL_APPROVE_LEDGER=$ApproveLedger" -ForegroundColor Gray
    Write-Host "GOV_COMMIT_CAP_HR=$Global:CommitLimit_Hourly" -ForegroundColor Gray
    Write-Host "GOV_ICU_CAP_HR=$Global:CommitLimit_ICU_Hourly" -ForegroundColor Gray

    # Write PID for Drill Safety
    Write-Host "Debug: Writing PID..."
    $PidFile = Join-Path $Root "Runtime\State\console_server.pid"
    if (-not (Test-Path (Split-Path $PidFile))) { New-Item -ItemType Directory (Split-Path $PidFile) -Force | Out-Null }
    [System.Diagnostics.Process]::GetCurrentProcess().Id | Out-File $PidFile -Force

    # SSE Tracking
    $Global:SseJobs = @{}
    
    Write-Host "API Module Loaded. PID: $((Get-Content $PidFile))" -ForegroundColor Green

    # --- Phase 68 Approval Helpers ---
    $ApprovalStatePath = Join-Path $GovDir "Approval_State.json"
    
    function Get-ApprovalState {
        $now = [DateTime]::UtcNow
        $hourBucket = $now.ToString("yyyy-MM-ddTHH")
        $defaults = @{
            current_hour_bucket = $hourBucket
            hourly_commit_count = 0
            hourly_icu_usage    = 0
            last_approval_ts    = [DateTime]::MinValue.ToString("o")
        }
        if (Test-Path $ApprovalStatePath) {
            try {
                $state = Get-Content $ApprovalStatePath | ConvertFrom-Json
                if ($state.current_hour_bucket -ne $hourBucket) {
                    return [PSCustomObject]$defaults
                }
                return $state
            }
            catch { return [PSCustomObject]$defaults }
        }
        return [PSCustomObject]$defaults
    }

    function Save-ApprovalState {
        param($State)
        $State | ConvertTo-Json | Set-Content $ApprovalStatePath -Force
    }

    function Get-ApprovalToken {
        param($ProposalId, $ProposalHash, $ExpiryUtc, $Actor)
        $msg = "${ProposalId}|${ProposalHash}|${ExpiryUtc}|${Actor}"
        $secret = [System.Text.Encoding]::UTF8.GetBytes($Global:ApprovalSecret)
        $hasher = New-Object System.Security.Cryptography.HMACSHA256
        $hasher.Key = $secret
        $hashBytes = $hasher.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($msg))
        return [Convert]::ToBase64String($hashBytes)
    }

    function Verify-ApprovalToken {
        param($Token, $ProposalId, $ProposalHash, $ExpiryUtc, $Actor)
        $expected = Get-ApprovalToken -ProposalId $ProposalId -ProposalHash $ProposalHash -ExpiryUtc $ExpiryUtc -Actor $Actor
        if ($Token -ne $expected) { return @{ ok = $false; reason = "Token Mismatch (Integrity Violation)" } }
        
        $exp = [DateTime]::Parse($ExpiryUtc).ToUniversalTime()
        if ([DateTime]::UtcNow -gt $exp) { return @{ ok = $false; reason = "Token Expired (TTL Violation). Now: $([DateTime]::UtcNow.ToString('o')), Exp: $($exp.ToString('o'))" } }
        
        return @{ ok = $true }
    }

    function Check-CommitBudget {
        param($IcuCost)
        $state = Get-ApprovalState
        if ($state.hourly_commit_count -ge $Global:CommitLimit_Hourly) {
            return @{ ok = $false; reason = "Commit Cap Exceeded ($($Global:CommitLimit_Hourly)/hr)" }
        }
        if (($state.hourly_icu_usage + $IcuCost) -gt $Global:CommitLimit_ICU_Hourly) {
            return @{ ok = $false; reason = "ICU Cap Exceeded ($($Global:CommitLimit_ICU_Hourly)/hr)" }
        }
        return @{ ok = $true; state = $state }
    }

    # --- Pulse Producer (Background) ---
    if ($Global:PulseJob -and $Global:PulseHandle -and -not $Global:PulseHandle.IsCompleted) {
        Write-Host "Pulse Producer is already active." -ForegroundColor Yellow
    }
    else {
        # Cleanup potential stale object
        if ($Global:PulseJob) { try { $Global:PulseJob.Dispose() } catch {} }

        # Stop flag for producer loop
        $Global:PulseStop = $false

        Write-Host "Starting Pulse Producer (Background Heartbeat)..." -ForegroundColor Cyan
        $Global:PulseJob = [PowerShell]::Create()
        [void]$Global:PulseJob.AddScript({
                param($PulseLedger, $WatchdogScript)
                try {
                    "Pulse Producer Started. Script: $WatchdogScript, Ledger: $PulseLedger" | Out-File "D:\Infinite\Infinity\Console\pulse_debug.log" -Append
                
                    while ($true) {
                        try {
                            & $WatchdogScript -Mode "FAST" *>$null
                        
                            if ($LASTEXITCODE -ne 0) {
                                "Pulse Failed ExitCode: $LASTEXITCODE" | Out-File "D:\Infinite\Infinity\Console\pulse_debug.log" -Append
                            }
                        }
                        catch {
                            "Pulse Loop Error: $_" | Add-Content -Path "D:\Infinite\Infinity\Console\pulse_debug.log" -Encoding utf8
                        }
                    
                        Start-Sleep -Seconds 5
                    }
                }
                catch {
                    "Pulse Producer Stopping: $_" | Add-Content -Path "D:\Infinite\Infinity\Console\pulse_debug.log" -Encoding utf8
                }
            })
        [void]$Global:PulseJob.AddArgument($PulseLedger)
        [void]$Global:PulseJob.AddArgument((Join-Path $GovDir "Axis_Runtime_Integrity_Watchdog.ps1"))
        
        # Suppress output of BeginInvoke
        $Global:PulseHandle = $Global:PulseJob.BeginInvoke()
    }

    # --- Witness Scheduler (Background) ---
    if ($Global:SchedJob -and $Global:SchedHandle -and -not $Global:SchedHandle.IsCompleted) {
        Write-Host "Witness Scheduler is already active." -ForegroundColor Yellow
    }
    else {
        if ($Global:SchedJob) { try { $Global:SchedJob.Dispose() } catch {} }
        
        Write-Host "Starting Witness Scheduler (1m Cadence)..." -ForegroundColor Cyan
        $Global:SchedJob = [PowerShell]::Create()
        [void]$Global:SchedJob.AddScript({
                param($ModulePath, $KernelUrl, $PulsePath, $WitnessPath)
                $LogPath = "D:\Infinite\Infinity\Console\sched_debug.log"
                try {
                    $Now = [DateTime]::UtcNow.ToString("o")
                    "[$Now] WITNESS_LEDGER_PATH=$WitnessPath" | Add-Content -Path $LogPath -Encoding utf8
                    "[$Now] Scheduler Job Started. Module: $ModulePath, URL: $KernelUrl" | Add-Content -Path $LogPath -Encoding utf8
                    Import-Module $ModulePath -Force
                    "[$Now] Scheduler Module Imported Successfully." | Add-Content -Path $LogPath -Encoding utf8
                
                    while ($true) {
                        try {
                            Invoke-WitnessScheduler -KernelUrl $KernelUrl -PulseLedgerPath $PulsePath -WitnessLedgerPath $WitnessPath
                        }
                        catch {
                            $TickError = [DateTime]::UtcNow.ToString("o")
                            "[$TickError] Scheduler Logic Error: $_" | Out-File $LogPath -Append
                            $_.ScriptStackTrace | Out-File $LogPath -Append
                        }
                        Start-Sleep -Seconds 60
                    }
                }
                catch {
                    $FatalTime = [DateTime]::UtcNow.ToString("o")
                    "[$FatalTime] Scheduler Fatal Thread Abort: $_" | Out-File $LogPath -Append
                    $_.ScriptStackTrace | Out-File $LogPath -Append
                }
            })
        [void]$Global:SchedJob.AddArgument($SchedulerModule)
        [void]$Global:SchedJob.AddArgument("http://127.0.0.1:$Port")
        [void]$Global:SchedJob.AddArgument($PulseLedger)
        [void]$Global:SchedJob.AddArgument($WitnessLedger)
        $Global:SchedHandle = $Global:SchedJob.BeginInvoke()
    }


    # --- Listener Setup ---
    $listener = [System.Net.HttpListener]::new()
    $listener.Prefixes.Add("http://127.0.0.1:$Port/")
    $listener.Start()

    Write-Host "Listening on http://127.0.0.1:$Port/" -ForegroundColor Cyan
    Write-Host "Press Ctrl+C to stop." -ForegroundColor Gray

    # --- Main Loop ---
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response
        
        $path = $request.Url.LocalPath
        $query = $request.QueryString
        
        Write-Host "$($request.HttpMethod) $path" -ForegroundColor DarkGray
        
        # CORS (expand for fetch POST)
        $response.AddHeader("Access-Control-Allow-Origin", "*")
        $response.AddHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        $response.AddHeader("Access-Control-Allow-Headers", "Content-Type")

        # Preflight
        if ($request.HttpMethod -eq "OPTIONS") {
            $response.StatusCode = 204
            $response.Close()
            continue
        }

        # Method gate (allow POST only for witness endpoints)
        $allowPost = @("/api/witness/propose", "/api/witness/commit", "/api/witness/approve", "/api/witness/reject")
        if ($request.HttpMethod -ne "GET" -and -not ($request.HttpMethod -eq "POST" -and $allowPost -contains $path)) {
            $response.StatusCode = 405
            $response.Close()
            continue
        }

        try {
            $content = $null
            $json = $null
            $handledByJob = $false
            
            # --- Routing ---
            
            # 1. Static Files
            if ($path -eq "/" -or $path -eq "/index.html") {
                $filePath = Join-Path $PublicDir "index.html"
                if (Test-Path $filePath) {
                    $content = [System.IO.File]::ReadAllBytes($filePath)
                    $response.ContentType = "text/html"
                }
                else {
                    $response.StatusCode = 404
                }
            }
            elseif ($path -like "/public/*") {
                # Security: Use proper substring and path check (Fixes TrimStart bug)
                $rel = $path.Substring("/public/".Length)
                $filePath = Join-Path $PublicDir $rel
                $fullPath = [System.IO.Path]::GetFullPath($filePath)
                $publicRoot = [System.IO.Path]::GetFullPath($PublicDir)

                # Strict Traversal Check
                if ((Test-Path $fullPath) -and $fullPath.StartsWith($publicRoot, [StringComparison]::OrdinalIgnoreCase)) {
                    $content = [System.IO.File]::ReadAllBytes($fullPath)
                    switch ([System.IO.Path]::GetExtension($fullPath)) {
                        ".js" { $response.ContentType = "application/javascript" }
                        ".css" { $response.ContentType = "text/css" }
                        ".png" { $response.ContentType = "image/png" }
                        default { $response.ContentType = "application/octet-stream" }
                    }
                }
                else {
                    $response.StatusCode = 404
                }
            }
            # 2. API Routes
            elseif ($path -eq "/api/status") {
                $data = Get-ConsoleStatus
                $json = $data | ConvertTo-Json -Depth 5 -Compress
                $response.ContentType = "application/json"
            }
            elseif ($path -eq "/api/find") {
                $key = $query["key"]
                $data = Find-AxisRecord -Key $key
                $json = $data | ConvertTo-Json -Depth 5 -Compress
                $response.ContentType = "application/json"
            }
            elseif ($path -eq "/api/pulses") {
                $count = if ($query["count"]) { [int]$query["count"] } else { 50 }
                $data = Get-PulseHistory -Count $count
                $json = $data | ConvertTo-Json -Depth 5 -Compress
                $response.ContentType = "application/json"
            }
            elseif ($path -eq "/api/anchors") {
                $count = if ($query["count"]) { [int]$query["count"] } else { 50 }
                $data = Get-AnchorHistory -Count $count
                $json = $data | ConvertTo-Json -Depth 5 -Compress
                $response.ContentType = "application/json"
            }
            elseif ($path -eq "/api/warm/verify") {
                $data = Get-WarmStorageReport
                $json = $data | ConvertTo-Json -Depth 6 -Compress
                $response.ContentType = "application/json"
            }
            # 3. Econ Routes
            elseif ($path -eq "/api/econ/status") {
                $data = Get-EconStatus
                $json = $data | ConvertTo-Json -Depth 5 -Compress
                $response.ContentType = "application/json"
            }
            elseif ($path -eq "/api/econ/history") {
                $count = if ($query["count"]) { [int]$query["count"] } else { 200 }
                $data = Get-EconHistory -Count $count
                $json = $data | ConvertTo-Json -Depth 5 -Compress
                $response.ContentType = "application/json"
            }
            elseif ($path -eq "/api/econ/policy") {
                $polFile = Join-Path $Root "Governance\Economics\econ_policy.json"
                if (Test-Path $polFile) {
                    $json = Get-Content $polFile -Raw
                    $response.ContentType = "application/json"
                }
                else {
                    $response.StatusCode = 404
                }
            }
            # 4. Provenance Routes
            elseif ($path -eq "/api/provenance/trail") {
                $key = $query["key"]
                
                # 1. Estimate Cost
                $cost = Estimate-Cost -Key $key
                
                # 2. Check Budget
                $check = Check-EconBudget -Cost $cost
                if (-not $check.allowed) {
                    $response.StatusCode = 429 # Too Many Requests
                    $json = @{ error = "Budget Exceeded"; reason = $check.reason; status = $check.status } | ConvertTo-Json -Compress
                    $response.ContentType = "application/json"
                }
                else {
                    # 3. Debit Ledger
                    # We debit 'ProvenanceQuery'
                    Write-EconEvent -Component "Console" -Action "ProvenanceQuery" -Mode "FAST" -DurationMs 0 -Ref @{ key = $key } -NoRebuild | Out-Null
                    
                    # 4. Execute
                    $data = Get-ProvenanceTrail -Key $key
                    $responseObj = @{
                        ok       = $true
                        debit    = $cost
                        currency = "ICU"
                        status   = $check.status
                        trail    = $data
                    }
                    $json = $responseObj | ConvertTo-Json -Depth 5 -Compress
                    $response.ContentType = "application/json"
                }
            }
            # 5. Witness Writer Routes (Phase 66)
            elseif ($path -eq "/api/witness/propose" -and $request.HttpMethod -eq "POST") {
                # Read Body
                $reader = [System.IO.StreamReader]::new($request.InputStream)
                $body = $reader.ReadToEnd()
                $payload = $body | ConvertFrom-Json

                # 1. Calculate Cost Estimate (Deterministics)
                # bytes = JSON length
                $bytes = $body.Length
                $units = [Math]::Ceiling($bytes / 4096)
                $costEst = [Math]::Min([Math]::Max($units, 1), 25)

                # 2. Policy Check
                # Hardcoded strictness: All witness writes require anchor logic
                # (In this RC1, we just flag it as 'requires_anchor=true')
                
                # 3. Create Proposal Record
                $proposalId = Get-FileHash -InputStream ([System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes($body))) -Algorithm SHA256 | Select-Object -ExpandProperty Hash
                
                $proposal = @{
                    kind        = "WITNESS_PROPOSAL"
                    proposal_id = $proposalId
                    ts_utc      = [DateTime]::UtcNow.ToString("o")
                    source      = @{
                        source_id    = $payload.source_id
                        selected_key = $payload.selected_key
                        origin       = "cockpit"
                    }
                    intent      = @{
                        action = $payload.action
                        note   = $payload.note
                        tags   = $payload.tags
                    }
                    payload     = $payload.payload # pulse, trail, graph
                    econ        = @{
                        cost_estimate_icu = $costEst
                        cost_basis        = @{ bytes = $bytes }
                    }
                    policy      = @{
                        requires_anchor = $true
                        reason          = "Canonical Witness Ledger Write"
                        risk            = "MED"
                    }
                    status      = "PROPOSED"
                }

                # 4. Save to Staged Proposals
                $propFile = $PropLedger
                $jsonLine = $proposal | ConvertTo-Json -Depth 10 -Compress
                Add-Content -Path $propFile -Value $jsonLine -Encoding utf8

                # 5. Return Preview
                $responseObj = @{
                    proposal_id       = $proposalId
                    preview           = @{
                        would_write = "witness_ledger"
                        witness_key = "sha256:..." # simplistic placeholder
                    }
                    cost_estimate_icu = $costEst
                    requires_anchor   = $true
                    reason            = "canonical_write"
                    risk              = "MED"
                }
                $json = $responseObj | ConvertTo-Json -Depth 5 -Compress
                $response.ContentType = "application/json"
            }
            elseif ($path -eq "/api/witness/pending") {
                # GET /api/witness/pending
                if (-not (Test-Path $PropLedger)) {
                    $json = @() | ConvertTo-Json
                }
                else {
                    $lines = Get-Content $PropLedger -ErrorAction SilentlyContinue
                    $pending = @()
                    foreach ($l in $lines) {
                        try {
                            $o = $l | ConvertFrom-Json
                            if ($o.status -eq "PROPOSED") { $pending += $o }
                        }
                        catch {}
                    }
                    $limit = if ($query["limit"]) { [int]$query["limit"] } else { 50 }
                    $json = $pending | Select-Object -Last $limit | ConvertTo-Json -Depth 5 -Compress
                }
                $response.ContentType = "application/json"
            }
            elseif ($path -eq "/api/witness/approve" -and $request.HttpMethod -eq "POST") {
                # POST /api/witness/approve { proposal_id, actor }
                $reader = [System.IO.StreamReader]::new($request.InputStream)
                $body = $reader.ReadToEnd()
                $payload = $body | ConvertFrom-Json
                
                $propId = $payload.proposal_id
                $actor = if ($payload.actor) { $payload.actor } else { "ANCHOR" }
                
                # 1. Find Proposal
                $found = $null
                if (Test-Path $PropLedger) {
                    $lines = Get-Content $PropLedger
                    foreach ($l in $lines) {
                        try {
                            $o = $l | ConvertFrom-Json
                            if ($o.proposal_id -eq $propId) { $found = $o; break }
                        }
                        catch {}
                    }
                }
                
                if (-not $found) {
                    $response.StatusCode = 404
                    $json = @{ error = "Proposal not found" } | ConvertTo-Json -Compress
                }
                elseif ($found.status -ne "PROPOSED") {
                    $response.StatusCode = 409
                    $json = @{ error = "Invalid Status"; status = $found.status } | ConvertTo-Json -Compress
                }
                else {
                    # 2. Mint Token
                    $expiry = [DateTime]::UtcNow.AddMinutes(15).ToString("o")
                    # We hash the original proposal JSON for content integrity
                    $propHash = Get-FileHash -InputStream ([System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes(($found | ConvertTo-Json -Depth 10 -Compress)))) -Algorithm SHA256 | Select-Object -ExpandProperty Hash
                    
                    $token = Get-ApprovalToken -ProposalId $propId -ProposalHash $propHash -ExpiryUtc $expiry -Actor $actor
                    
                    # 3. Log Approval
                    $logEntry = @{
                        ts_utc      = [DateTime]::UtcNow.ToString("o")
                        action      = "APPROVE"
                        actor       = $actor
                        proposal_id = $propId
                        token_hash  = (Get-FileHash -InputStream ([System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes($token))) -Algorithm SHA256).Hash
                    }
                    $logEntry | ConvertTo-Json -Compress | Add-Content -Path $ApproveLedger -Encoding utf8
                    
                    $json = @{
                        ok             = $true
                        approval_token = $token
                        expires_utc    = $expiry
                        proposal_hash  = $propHash
                        proposal_id    = $propId
                    } | ConvertTo-Json -Compress
                }
                $response.ContentType = "application/json"
            }
            elseif ($path -eq "/api/witness/reject" -and $request.HttpMethod -eq "POST") {
                # POST /api/witness/reject { proposal_id, reason, actor }
                $reader = [System.IO.StreamReader]::new($request.InputStream)
                $body = $reader.ReadToEnd()
                $payload = $body | ConvertFrom-Json
                
                $propId = $payload.proposal_id
                $reason = $payload.reason
                $actor = if ($payload.actor) { $payload.actor } else { "ANCHOR" }
                
                # Update Proposal Status (In-place file update for JSONL is slow, but we'll append a status event or rewrite for RC1)
                # Actually, our 'Lookup' finds the FIRST one. We should ideally find the LAST one if we append status updates.
                # For Phase 68, we'll append a "status update" entry to the proposals ledger OR just log it in approvals.
                # Let's append to approvals and treat approvals as the state source for 'final' status.
                
                $logEntry = @{
                    ts_utc      = [DateTime]::UtcNow.ToString("o")
                    action      = "REJECT"
                    actor       = $actor
                    proposal_id = $propId
                    reason      = $reason
                }
                $logEntry | ConvertTo-Json -Compress | Add-Content -Path $ApproveLedger -Encoding utf8
                
                # Optional: We could mark it REJECTED in a status ledger. 
                # For now, we'll just return OK.
                $json = @{ ok = $true } | ConvertTo-Json -Compress
                $response.ContentType = "application/json"
            }
            elseif ($path -eq "/api/witness/commit" -and $request.HttpMethod -eq "POST") {
                # Read Body
                $reader = [System.IO.StreamReader]::new($request.InputStream)
                $body = $reader.ReadToEnd()
                $req = $body | ConvertFrom-Json
                
                $propId = $req.proposal_id
                $token = $req.approval_token
                $actor = if ($req.actor) { $req.actor } else { "ANCHOR" }
                $expiry = $req.expires_utc
                $propHash = $req.proposal_hash

                # 1. Lookup Proposal (Scan from end for latest status)
                $found = $null
                if (Test-Path $PropLedger) {
                    $lines = Get-Content $PropLedger
                    # Find original proposal
                    foreach ($l in $lines) {
                        try {
                            $o = $l | ConvertFrom-Json
                            if ($o.proposal_id -eq $propId -and $o.kind -eq "WITNESS_PROPOSAL") { $found = $o; break }
                        }
                        catch {}
                    }
                }

                if (-not $found) {
                    $response.StatusCode = 404
                    $json = @{ error = "Proposal not found" } | ConvertTo-Json -Compress
                }
                else {
                    # 2. Check for Rejection/previous Commit in approvals ledger
                    $isBlocked = $false
                    if (Test-Path $ApproveLedger) {
                        $appLines = Get-Content $ApproveLedger
                        foreach ($al in $appLines) {
                            try {
                                $ao = $al | ConvertFrom-Json
                                if ($ao.proposal_id -eq $propId) {
                                    if ($ao.action -eq "REJECT") { $isBlocked = "REJECTED" }
                                    if ($ao.action -eq "COMMIT") { $isBlocked = "ALREADY_COMMITTED" }
                                }
                            }
                            catch {}
                        }
                    }

                    if ($isBlocked) {
                        $response.StatusCode = 409
                        $json = @{ error = "Proposal $isBlocked" } | ConvertTo-Json -Compress
                    }
                    else {
                        # 3. Verify Token Integrity
                        $v = Verify-ApprovalToken -Token $token -ProposalId $propId -ProposalHash $propHash -ExpiryUtc $expiry -Actor $actor
                        if (-not $v.ok) {
                            $response.StatusCode = 403
                            $json = @{ error = "Unauthorized"; reason = $v.reason } | ConvertTo-Json -Compress
                        }
                        else {
                            # 4. Content Integrity (Hash Check)
                            $currentHash = Get-FileHash -InputStream ([System.IO.MemoryStream]::new([System.Text.Encoding]::UTF8.GetBytes(($found | ConvertTo-Json -Depth 10 -Compress)))) -Algorithm SHA256 | Select-Object -ExpandProperty Hash
                            if ($currentHash -ne $propHash) {
                                $response.StatusCode = 409
                                $json = @{ error = "Content Mismatch"; reason = "Proposal has been modified since approval." } | ConvertTo-Json -Compress
                            }
                            else {
                                # 5. Budget Check
                                $cost = $found.econ.cost_estimate_icu
                                $budget = Check-CommitBudget -IcuCost $cost
                                if (-not $budget.ok) {
                                    $response.StatusCode = 429
                                    $json = @{ error = "Bounded Authority Exceeded"; reason = $budget.reason } | ConvertTo-Json -Compress
                                }
                                else {
                                    # 6. ATOMIC LOCK
                                    $lockPath = Join-Path $GovDir ".locks\proposal_$propId.lock"
                                    try {
                                        New-Item -Path $lockPath -ItemType File -Value $null -ErrorAction Stop | Out-Null
                                    }
                                    catch {
                                        $response.StatusCode = 409
                                        $json = @{ error = "Conflict"; reason = "Commit already in progress or completed." } | ConvertTo-Json -Compress
                                        return # Exit block
                                    }

                                    try {
                                        # 7. Write Canonical Witness
                                        $witness = @{
                                            kind        = "WITNESS_COMMIT"
                                            proposal_id = $propId
                                            witness_key = $found.source.selected_key
                                            ts_utc      = [DateTime]::UtcNow.ToString("o")
                                            approval    = @{ token_hash = $token.Substring(0, 10) + "..."; actor = $actor }
                                            econ        = @{ cost_icu = $cost }
                                            payload     = $found.payload
                                            status      = "COMMITTED"
                                        }
                                        $witness | ConvertTo-Json -Depth 10 -Compress | Add-Content -Path $WitnessLedger -Encoding utf8
                                        
                                        # 8. Log Final Approval (COMMIT)
                                        $commitLog = @{
                                            ts_utc      = [DateTime]::UtcNow.ToString("o")
                                            action      = "COMMIT"
                                            actor       = $actor
                                            proposal_id = $propId
                                            cost        = $cost
                                        }
                                        $commitLog | ConvertTo-Json -Compress | Add-Content -Path $ApproveLedger -Encoding utf8

                                        # 9. Update State (Counters)
                                        $newState = $budget.state
                                        $newState.hourly_commit_count++
                                        $newState.hourly_icu_usage += $cost
                                        Save-ApprovalState $newState

                                        # 10. Debit Econ
                                        Write-EconEvent -Component "Console" -Action "WitnessCommit" -Mode "FAST" -DurationMs 0 -Ref @{ proposal = $propId } -NoRebuild -UnitsOverride $cost | Out-Null

                                        $responseObj = @{
                                            committed     = $true
                                            witness_key   = $witness.witness_key
                                            write_receipt = @{ ts_utc = $witness.ts_utc; cost_icu = $cost }
                                        }
                                        $json = $responseObj | ConvertTo-Json -Depth 5 -Compress
                                    }
                                    finally {
                                        Remove-Item $lockPath -Force -ErrorAction SilentlyContinue
                                    }
                                }
                            }
                        }
                    }
                }
                $response.ContentType = "application/json"
            }
            elseif ($path -eq "/api/provenance/graph") {
                $key = $query["key"]
                $mode = if ($query["mode"]) { $query["mode"] } else { "Event" }
                
                # 1. Base Cost Check + Predictive Expansion Check
                $baseCost = switch ($mode) {
                    "Claim" { 30.0 }
                    "Coin" { 40.0 }
                    Default { 20.0 }
                }
                
                # Predictive: Base + (Max Expansions * CostPerExpansion)
                # We assume worst case: every node triggers an expansion.
                $maxNodes = 50
                $expandCost = 2.0
                $projectedWorstCase = $baseCost + ($maxNodes * $expandCost)
                
                $check = Check-EconBudget -Cost $projectedWorstCase
                
                if (-not $check.allowed) {
                    $response.StatusCode = 429
                    $json = @{ error = "Budget Exceeded (Predictive)"; reason = $check.reason; status = $check.status; projected = $projectedWorstCase } | ConvertTo-Json -Compress
                }
                else {
                    # 2. Execute Graph (Bounded)
                    $graphData = Get-ProvenanceGraph -Key $key -Mode $mode -MaxNodes 50 -MaxEdges 100
                     
                    # 3. Calculate Final Cost
                    # Base + 2 per expansion
                    $expandCost = 2.0
                    $expansions = $graphData.stats.expansions
                    $totalCost = $baseCost + ($expansions * $expandCost)
                     
                    $action = switch ($mode) {
                        "Claim" { "ClaimGraph" }
                        "Coin" { "CoinFlow" }
                        Default { "ProvenanceGraph" }
                    }

                    # 4. Debit
                    # IMPORTANT: econ Mode should remain FAST unless your econ weights include CLAIM/COIN.
                    Write-EconEvent -Component "Console" -Action $action -Mode "FAST" -DurationMs 0 -Ref @{ key = $key; nodes = $graphData.stats.nodeCount; expansions = $expansions; graph_mode = $mode } -NoRebuild -UnitsOverride $totalCost | Out-Null
                     
                    # 5. Return
                    $responseObj = @{
                        ok       = $true
                        debit    = $totalCost
                        currency = "ICU"
                        status   = $check.status
                        graph    = $graphData.graph
                        stats    = $graphData.stats
                    }
                    $json = $responseObj | ConvertTo-Json -Depth 5 -Compress
                }
                $response.ContentType = "application/json"
            }
            elseif ($path -eq "/api/stream") {
                # Server-Sent Events (SSE)
                $response.AddHeader("Content-Type", "text/event-stream")
                $response.AddHeader("Cache-Control", "no-cache")
                $response.AddHeader("Connection", "keep-alive")
                $response.KeepAlive = $true
                
                # Cleanup dead jobs (Runspace Pattern) - Robust Expiry
                $now = Get-Date
                $dead = @()
                foreach ($k in $Global:SseJobs.Keys) {
                    $job = $Global:SseJobs[$k]
                    if ($job.Handle.IsCompleted -or ($now - $job.StartTime).TotalSeconds -gt 90) { 
                        $dead += $k 
                    }
                }
                foreach ($k in $dead) {
                    $j = $Global:SseJobs[$k]
                    if ($j.Handle.IsCompleted) {
                        try { $j.PS.EndInvoke($j.Handle) } catch {}
                    }
                    try { $j.PS.Dispose() } catch {}
                    $Global:SseJobs.Remove($k)
                }

                # Cap Connections
                if ($Global:SseJobs.Count -ge 5) {
                    $response.StatusCode = 429
                    $response.StatusDescription = "Too Many Clients"
                    $json = @{ error = "Too many SSE clients"; limit = 5 } | ConvertTo-Json -Compress
                    $buffer = [System.Text.Encoding]::UTF8.GetBytes($json)
                    $response.ContentLength64 = $buffer.Length
                    $response.OutputStream.Write($buffer, 0, $buffer.Length)
                    $response.OutputStream.Write($buffer, 0, $buffer.Length)
                    $response.Close()
                    continue
                }

                $ctx = $context # Capture context
                $clientId = [Guid]::NewGuid().ToString()
                
                # Native Runspace (No Module Dependency)
                $ps = [PowerShell]::Create()
                [void]$ps.AddScript({
                        param($ctx, $pulseLedger, $econLedger, $propLedger)
                    
                        try {
                            $sseLog = "D:\Infinite\Infinity\Console\sse_debug.log"
                            "SSE Thread Started. Client: $ctx" | Add-Content -Path $sseLog -Encoding utf8
                        
                            $resp = $ctx.Response
                            $writer = New-Object System.IO.StreamWriter($resp.OutputStream, [System.Text.Encoding]::UTF8)
                            $writer.AutoFlush = $true
                        
                            $writer.WriteLine("event: connected")
                            $writer.WriteLine("data: {`"msg`":`"Stream Opened`"}")
                            $writer.WriteLine("")
                        
                            $lastPulseSize = 0
                            if (Test-Path $pulseLedger) { $lastPulseSize = (Get-Item $pulseLedger).Length }
                        
                            $lastEconSize = 0
                            if (Test-Path $econLedger) { $lastEconSize = (Get-Item $econLedger).Length }
                        
                            $lastPropSize = 0
                            if (Test-Path $propLedger) { $lastPropSize = (Get-Item $propLedger).Length }
                        
                            # Run for 60 seconds then close (Client reconnects) - Safer for resource leaks
                            for ($i = 0; $i -lt 60; $i++) {
                                Start-Sleep -Milliseconds 500
                            
                                # Check Pulse
                                if (Test-Path $pulseLedger) {
                                    $curSize = (Get-Item $pulseLedger).Length
                                    if ($curSize -gt $lastPulseSize) {
                                        $last = Get-Content $pulseLedger -Tail 1 -ErrorAction SilentlyContinue
                                        if ($last) { $last = $last -replace '^\uFEFF', '' }
                                        $writer.WriteLine("event: pulse")
                                        $writer.WriteLine("data: $last")
                                        $writer.WriteLine("")
                                        $lastPulseSize = $curSize
                                    }
                                }
                            
                                # Check Econ
                                if (Test-Path $econLedger) {
                                    $curSize = (Get-Item $econLedger).Length
                                    if ($curSize -gt $lastEconSize) {
                                        $last = Get-Content $econLedger -Tail 1
                                        $writer.WriteLine("event: econ")
                                        $writer.WriteLine("data: $last")
                                        $writer.WriteLine("")
                                        $lastEconSize = $curSize
                                    }
                                }

                                # Check Proposals
                                if (Test-Path $propLedger) {
                                    $curSize = (Get-Item $propLedger).Length
                                    if ($curSize -gt $lastPropSize) {
                                        $all = Get-Content $propLedger
                                        $pendingCount = ($all | Where-Object { ($_ | ConvertFrom-Json).status -eq "PROPOSED" }).Count
                                        $writer.WriteLine("event: pending_witness")
                                        $writer.WriteLine("data: {`"count`":$pendingCount}")
                                        $writer.WriteLine("")
                                        $lastPropSize = $curSize
                                    }
                                }
                            
                                # Keepalive
                                if ($i % 5 -eq 0) { 
                                    $writer.WriteLine(": ping") 
                                    $writer.WriteLine("")
                                }
                            }
                            $writer.WriteLine("event: close")
                            $writer.WriteLine("data: {`"reason`":`"timeout`"}")
                            $writer.WriteLine("")
                        
                        }
                        catch {
                            # Client disconnected or error
                            $sseLog = "D:\Infinite\Infinity\Console\sse_debug.log"
                            "SSE Error: $_" | Add-Content -Path $sseLog -Encoding utf8
                            $_.ScriptStackTrace | Add-Content -Path $sseLog -Encoding utf8
                        }
                        finally {
                            try { $resp.Close() } catch {}
                        }
                    })
                [void]$ps.AddArgument($ctx)
                [void]$ps.AddArgument($PulseLedger)
                [void]$ps.AddArgument($EconLedger)
                [void]$ps.AddArgument($PropLedger)
                
                $handle = $ps.BeginInvoke()
                
                $Global:SseJobs[$clientId] = @{ PS = $ps; Handle = $handle; StartTime = (Get-Date) }
                
                # We do NOT close response here. The Job closes it.
                $handledByJob = $true
                continue # Skip remaining logic for this iteration, do NOT exit script
            }
            else {
                $response.StatusCode = 404
            }

            # --- Response Writing ---
            if ($json) {
                $buffer = [System.Text.Encoding]::UTF8.GetBytes($json)
                $response.ContentLength64 = $buffer.Length
                $response.OutputStream.Write($buffer, 0, $buffer.Length)
            }
            elseif ($content) {
                $response.ContentLength64 = $content.Length
                $response.OutputStream.Write($content, 0, $content.Length)
            }
            
        }
        catch {
            # --- 500 Error Handling ---
            $response.StatusCode = 500
            $err = "$_" + "`n" + ($_.ScriptStackTrace | Out-String)
            
            # Log to file
            $errLog = "D:\Infinite\Infinity\Console\server_error.log"
            $err | Add-Content -Path $errLog -Encoding utf8
            
            # Send to client
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($err)
            $response.ContentLength64 = $bytes.Length
            $response.OutputStream.Write($bytes, 0, $bytes.Length)
            
            Write-Host "Error: $_" -ForegroundColor Red
        }
        finally {
            if (-not $handledByJob) {
                $response.Close()
            }
        }
    }
}
catch {
    Write-Host "FATAL SERVER ERROR: $_" -ForegroundColor Red
    $_.ScriptStackTrace | Out-String | Write-Host -ForegroundColor Red
}
finally {
    if ($listener -and $listener.IsListening) {
        $listener.Stop()
    }
    
    # Cleanup Pulse Job
    if ($Global:PulseJob) {
        Write-Host "Stopping Pulse Producer..." -ForegroundColor Yellow
        try {
            if ($Global:PulseHandle -and $Global:PulseHandle.IsCompleted) {
                $Global:PulseJob.EndInvoke($Global:PulseHandle) 
            }
        }
        catch {}
        try { $Global:PulseJob.Dispose() } catch {}
        $Global:PulseJob = $null
        $Global:PulseHandle = $null
    }
}
