# T17_SegmentEnumerator.psm1

function Get-LedgerSegments {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string]$ActivePath
    )
    
    $dir = Split-Path $ActivePath -Parent
    $archiveDir = Join-Path $dir "Archive"
    
    # Force array treatment to prevent PS string unwrapping
    $segments = @()
    
    # 1. Find Archives (name.YYYY-MM.jsonl)
    if (Test-Path $archiveDir) {
        $files = Get-ChildItem -Path $archiveDir -Filter "$Name.*.jsonl" | Sort-Object Name
        foreach ($f in $files) { $segments += $f.FullName }
    }
    
    # 2. Add Active
    if (Test-Path $ActivePath) {
        $segments += $ActivePath
    }
    
    return $segments
}

Export-ModuleMember -Function Get-LedgerSegments
