param(
    [string]$ResultsPath = "D:\Infinite\Infinity\Truth_Engine\Research\TE_Research_Results.jsonl",
    [string]$TruthEnginePath = "D:\Infinite\Axis_Truth_Engine.ps1"
)

# 1. Load Results
if (-not (Test-Path $ResultsPath)) {
    Write-Host "[TR04] No results to assimilate." -ForegroundColor Gray
    return
}

$results = @(Get-Content $ResultsPath | ForEach-Object { $_ | ConvertFrom-Json })
$ingestedCount = 0

# 2. Ingest Observations via Truth Engine Core
foreach ($res in $results) {
    if ($res.outcome.status -eq "success") {
        Write-Host "[TR04] Ingesting research outcome for $($res.target_claim_id)..." -ForegroundColor Gray
        
        $payload = [PSCustomObject]@{
            Channel    = "INTERNAL-RESEARCH"
            Location   = "TRUTH-RESEARCH-001:$($res.probe_id)"
            ParentHint = $res.target_claim_id
            Agent      = "Axis_Researcher"
            Source     = "TRUTH-RESEARCH-001"
            Content    = "RESEARCH_CORROBORATION: $($res.outcome.evidence) (Target: $($res.target_claim_id))"
        }

        # Call the core Truth Engine to handle hashing, logging, and strategy triggering
        $ingestResult = & $TruthEnginePath -Action "INGEST" -Payload $payload
        if ($ingestResult.obs_id) { $ingestedCount++ }
    }
}

Write-Host "[TR04] Assimilated $ingestedCount research-derived observations via Truth Engine core." -ForegroundColor Cyan
