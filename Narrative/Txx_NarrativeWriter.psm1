<#
.SYNOPSIS
  Living Syntax Writer (Meaning Ledger)
.DESCRIPTION
  Writes narrative entries to living_syntax.jsonl.
  ENFORCES: scope = "NON_OPERATIVE"
  This ensures 'Meaning' never accidentally becomes 'Control'.
#>

$NarrativeDir = "D:\Infinite\Infinity\Narrative"
$LedgerPath = Join-Path $NarrativeDir "living_syntax.jsonl"

function Add-LivingSyntaxEntry {
  param(
    [Parameter(Mandatory)][string]$Id,
    [Parameter(Mandatory)][string]$Title,
    [Parameter(Mandatory)][object[]]$Claims, # @{type=; text=}
    [hashtable]$Evidence = @{},
    [string[]]$Links = @()
  )

  # 1. Enforce Scope
  $entry = [ordered]@{
    ts_utc    = (Get-Date).ToUniversalTime().ToString("o")
    syntax_id = $Id
    title     = $Title
    scope     = "NON_OPERATIVE"  # HARDCODED CONSTRAINT
    claims    = $Claims
    evidence  = $Evidence
    links     = $Links
  }

  # 2. Append
  $json = $entry | ConvertTo-Json -Compress -Depth 5
  Add-Content -Path $LedgerPath -Value $json -Encoding UTF8
    
  Write-Host "Written Meaning: $Id ($Title)" -ForegroundColor Cyan
}

function Add-LivingSyntaxJudgment {
  param(
    [Parameter(Mandatory)][string]$Subject,
    [Parameter(Mandatory)][string]$Observation,
    [Parameter(Mandatory)][string]$Verdict, # ALIGNED | MISALIGNED
    [string[]]$Evidence = @()
  )
    
  $entry = [ordered]@{
    ts_utc      = (Get-Date).ToUniversalTime().ToString("o")
    type        = "posthoc_judgment"
    subject     = $Subject
    observation = $Observation
    verdict     = $Verdict
    evidence    = $Evidence
    scope       = "NON_OPERATIVE"
  }

  $json = $entry | ConvertTo-Json -Compress -Depth 5
  Add-Content -Path $LedgerPath -Value $json -Encoding UTF8
    
  Write-Host "JUDGMENT: $Subject -> $Verdict" -ForegroundColor Yellow
}

Export-ModuleMember -Function Add-LivingSyntaxEntry, Add-LivingSyntaxJudgment
