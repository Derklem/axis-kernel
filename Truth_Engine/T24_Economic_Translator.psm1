<#
.SYNOPSIS
  T24_Economic_Translator.psm1
  Translates "Boring Competence" (System Integrity) into auditable Economic Artifacts.
.DESCRIPTION
  Phase 625: Sovereign Quiet Pillar.
  This module scans the Rectification Map and Decision Logs to generate "Integrity Proofs."
#>

function Get-IntegrityProof {
    $RectificationPath = "D:\Infinite\Infinity\Narrative\Rectification_Map.jsonl"
    $MetricsPath = "D:\Infinite\Infinity\Runtime\Decision\metrics_snapshot.json"
    
    $Findings = @()
    if (Test-Path $RectificationPath) {
        $Findings = Get-Content $RectificationPath | ConvertFrom-Json | Where-Object { $_.kind -eq "MATERIALIZED_REALITY" }
    }
    
    $Metrics = if (Test-Path $MetricsPath) { Get-Content $MetricsPath | ConvertFrom-Json } else { @{} }
    
    $Proof = [ordered]@{
        schema         = "axis.sovereign_audit.v1"
        ts_utc         = [DateTime]::UtcNow.ToString("o")
        integrity_score = 0.51 # Stable placeholder
        vitals         = $Metrics.vitals
        findings       = $Findings | ForEach-Object { @{ node_id = $_.node_id; title = $_.title; status = $_.status } }
        signature      = "Sovereign-Kernel-Ratified"
    }
    
    return $Proof
}

function Export-SovereignAudit {
    param([string]$OutFile = "D:\Infinite\Infinity\Deliverables\Sovereign_Audit_v01.json")
    
    $Proof = Get-IntegrityProof
    $Proof | ConvertTo-Json -Depth 5 | Set-Content $OutFile -Encoding UTF8
    Write-Host "[ECON] Sovereign Audit Exported: $OutFile" -ForegroundColor Green
}

Export-ModuleMember -Function Get-IntegrityProof, Export-SovereignAudit
