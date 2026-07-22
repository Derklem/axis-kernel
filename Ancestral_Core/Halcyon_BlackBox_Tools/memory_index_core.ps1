# === Memory Index Core ===
$target = "C:\Users\17602\Documents"
$index = @{}
$log = "C:\ProgramData\Halcyon\memory_index.txt"

Get-ChildItem -Path $target -Recurse -Include *.txt,*.json,*.log -ErrorAction SilentlyContinue | ForEach-Object {
    $c = Get-Content $_.FullName -ErrorAction SilentlyContinue
    foreach ($line in $c) {
        foreach ($word in ($line -split "\\W+")) {
            if ($word.Length -gt 4) { $index[$word] += 1 }
        }
    }
}
$index.GetEnumerator() | Sort-Object -Property Value -Descending | Select-Object -First 100 |
ForEach-Object { Add-Content -Path $log -Value "$(.Key): $(.Value)" }
