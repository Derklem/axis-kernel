function Invoke-AxisHandler {
    param(
        [Parameter(Mandatory = $true)] $Intent,
        [Parameter(Mandatory = $true)] $SystemMode
    )

    $ErrorActionPreference = "Stop"

    # Still read-only. This handler only produces a plan + evidence.
    if ($SystemMode.mode -ne "OBSERVATION_ONLY") {
        return [ordered]@{
            handled = $true; task = "repair_memory"; handler = "H_RepairMemory.ps1"
            status = "BLOCKED"; output = @{ reason = "SystemMode not OBSERVATION_ONLY" }
        }
    }

    $Root = "D:\Infinite\Infinity"
    $MemEvents = Join-Path $Root "Memory\ledger\events\memory_ingest_events.jsonl"
    $OffsetState = Join-Path $Root "Memory\ledger\state\t17_offset.json"

    $analysis = [ordered]@{
        ts_utc      = (Get-Date).ToUniversalTime().ToString("o")
        findings    = @()
        repair_plan = @()
    }

    if (Test-Path $MemEvents) {
        $last = @(Get-Content $MemEvents -Tail 2000)
        $errors = 0
        foreach ($ln in $last) {
            if ([string]::IsNullOrWhiteSpace($ln)) { continue }
            try { $o = $ln | ConvertFrom-Json } catch { continue }
            if ($o.schema -match "ingest\.error") { $errors++ }
        }
        $analysis.findings += [ordered]@{ kind = "ingest_errors_last2000"; count = $errors }
    }
    else {
        $analysis.findings += [ordered]@{ kind = "ingest_events_missing"; detail = $MemEvents }
    }

    if (Test-Path $OffsetState) {
        try {
            $st = Get-Content $OffsetState -Raw | ConvertFrom-Json
            $analysis.findings += [ordered]@{
                kind             = "offset_state"
                last_byte_offset = $st.last_byte_offset
                last_file_length = $st.last_file_length
                source_path      = $st.source_path
            }
        }
        catch {
            $analysis.findings += [ordered]@{ kind = "offset_state_unreadable"; detail = $OffsetState }
        }
    }

    # Repair plan is actions to take, not actions taken
    $analysis.repair_plan += "If ingest errors persist: rotate/segment source JSONL; validate line endings; identify non-JSON lines and writer source."
    $analysis.repair_plan += "If offset > file length: declare discontinuity, reset offset to 0 with new file_epoch (do not overwrite logs; append a discontinuity event)."
    $analysis.repair_plan += "Add Axis_Verify_T17 to Axis_Verify_All so drift heartbeat flags memory integrity."

    return [ordered]@{
        handled = $true
        task    = "repair_memory"
        handler = "H_RepairMemory.ps1"
        status  = "PLAN_ONLY"
        output  = $analysis
    }
}
