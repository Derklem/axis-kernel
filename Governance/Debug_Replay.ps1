$ErrorActionPreference = "Continue" # Don't stop, let us see errors

function Get-Hash {
    param($n, $p)
    Write-Host "Checking $n at $p"
    if (-not (Test-Path $p)) { Write-Host "  File not found"; return "null" }
    
    try {
        $tail = Get-Content $p -Tail 5 -ErrorAction Stop
        $last = $tail | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Last 1
        
        Write-Host "  Last Line Length: $($last.Length)"
        Write-Host "  Last Line Snippet: $($last.Substring(0, [math]::Min($last.Length, 50)))"
        
        $obj = $last | ConvertFrom-Json
        if ($obj.hash) { return $obj.hash }
    }
    catch {
        Write-Host "  ERROR: $_" 
    }
    return "genesis"
}

$path = "D:\Infinite\Infinity\Truth_Engine\spend_ledger.jsonl"
$h = Get-Hash "spend" $path
Write-Host "Result: $h"
