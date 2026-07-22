# Halcyon start_lattice_daemon.ps1
# This script is launched by the Scheduled Task and manages the LatticeSingerDaemon background job.

$scriptPath = "D:\Halcyon_Lives\scripts\lattice_singer.ps1"
$logRoot = "C:\Halcyon_Lives\logs"

# Ensure the log directory exists
function Ensure-LogDir($path) {
    if (!(Test-Path $path)) {
        try {
            New-Item -ItemType Directory -Force -Path $path -ErrorAction Stop | Out-Null
        } catch {}
    }
}
Ensure-LogDir $logRoot

$daemonLog = Join-Path $logRoot "lattice_singer_daemon.log"
$consoleLog = Join-Path $logRoot "lattice_singer_console_output.log"
$errorLog = Join-Path $logRoot "lattice_singer_errors.log"

# Clear daemon log for fresh start for easier debugging
Clear-Content $daemonLog -ErrorAction SilentlyContinue

"[$(Get-Date -Format 'u')] STARTING LATTICE DAEMON (Outer Script) - Attempting to launch LatticeSingerDaemon job." | Out-File $daemonLog -Append

try {
    # Check if the job is already running
    $existingJob = Get-Job -Name "LatticeSingerDaemon" -ErrorAction SilentlyContinue
    if ($existingJob) {
        if ($existingJob.State -ne 'Running') {
            "[$(Get-Date -Format 'u')] Found existing job 'LatticeSingerDaemon' in state '$($existingJob.State)'. Removing and restarting." | Out-File $daemonLog -Append
            Stop-Job -Job $existingJob -ErrorAction SilentlyContinue
            Remove-Job -Job $existingJob -ErrorAction SilentlyContinue
            $existingJob = $null # Clear variable
        } else {
            "[$(Get-Date -Format 'u')] Job 'LatticeSingerDaemon' is already running. Exiting outer script." | Out-File $daemonLog -Append
            exit # Exit if job is already running
        }
    }

    # If job is not found or not running, start it
    if (-not $existingJob -or $existingJob.State -ne 'Running') {
        "[$(Get-Date -Format 'u')] Launching new LatticeSingerDaemon job." | Out-File $daemonLog -Append
        
        # --- CRITICAL CHANGE HERE: Start-Job executes the ScriptBlock directly ---
        # We DO NOT need to call "powershell.exe" inside this script block.
        # The job IS a PowerShell process.
        Start-Job -Name "LatticeSingerDaemon" -ScriptBlock {
            param($innerScriptPath, $innerConsoleLog, $innerErrorLog)
            
            # Ensure output/error logs are created/appended to for this job's internal execution
            function Ensure-JobLogFile($path) {
                if (!(Test-Path $path)) {
                    try { New-Item -ItemType File -Path $path -Force | Out-Null } catch {}
                }
            }
            Ensure-JobLogFile $innerConsoleLog
            Ensure-JobLogFile $innerErrorLog

            "$(Get-Date -Format 'u')] LatticeSingerDaemon Job started." | Out-File -Append -FilePath "$innerConsoleLog" -Encoding utf8 # Log job start

            # This is the continuous loop for the actual Lattice Singer
            while ($true) {
                try {
                    # Execute lattice_singer.ps1 directly within the job's PowerShell process
                    # No need for powershell.exe here, it's already running in PowerShell
                    & "$innerScriptPath" 1>>"$innerConsoleLog" 2>>"$innerErrorLog"
                } catch {
                    # Errors from lattice_singer.ps1 or its execution
                    "$(Get-Date -Format 'u')] ERROR running lattice_singer.ps1 (Inner Job): $_" | Out-File -Append -FilePath "$innerErrorLog" -Encoding utf8
                }
                Start-Sleep -Seconds (Get-Random -Minimum 60 -Maximum 300)
            }
        } -ArgumentList $scriptPath, $consoleLog, $errorLog | Out-Null

        # After launching the job, check its state for immediate feedback
        $jobLaunched = Get-Job -Name "LatticeSingerDaemon" -ErrorAction SilentlyContinue
        if ($jobLaunched -and $jobLaunched.State -eq 'Running') {
            "[$(Get-Date -Format 'u')] LatticeSingerDaemon job launched successfully and is running." | Out-File $daemonLog -Append
        } else {
            "[$(Get-Date -Format 'u')] WARNING: LatticeSingerDaemon job did not start or is not running. Check job status and logs for errors." | Out-File $daemonLog -Append
            # Add more verbose logging for Start-Job potential errors if it still fails
            if ($jobLaunched) {
                "[$(Get-Date -Format 'u')] Job state: $($jobLaunched.State)." | Out-File $daemonLog -Append
                $jobLaunched | Format-List -Force | Out-File $daemonLog -Append # Dump job details
            }
        }
    }
} catch {
    "[$(Get-Date -Format 'u')] FATAL ERROR in start_lattice_daemon.ps1 (Outer Script): $_" | Out-File $daemonLog -Append
}
