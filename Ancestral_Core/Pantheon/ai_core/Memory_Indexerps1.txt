# Define paths
$shardsPath = "E:\Pantheon\memory\shards"
$outputPath = "E:\Pantheon\memory\shard_index.txt"

# Start file
"Shard Index Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Out-File -FilePath $outputPath

# Index files
Get-ChildItem -Path $shardsPath -Recurse | ForEach-Object {
    $line = "{0}`t{1}" -f $_.FullName, $_.LastWriteTime
    Add-Content -Path $outputPath -Value $line
}
