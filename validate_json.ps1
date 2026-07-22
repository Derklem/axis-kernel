$root = "D:\Infinite\Infinity"
$files = Get-ChildItem -Path $root -Filter *.json -Recurse
foreach ($f in $files) {
    try {
        $content = Get-Content $f.FullName -Raw -ErrorAction Stop
        if ([string]::IsNullOrWhiteSpace($content)) {
            Write-Host "EMPTY: $($f.FullName)"
            continue
        }
        $null = $content | ConvertFrom-Json -ErrorAction Stop
    }
    catch {
        Write-Host "BAD_JSON: $($f.FullName)"
        Write-Host "Error: $($_.Exception.Message)"
        Write-Host "--------------------"
    }
}
