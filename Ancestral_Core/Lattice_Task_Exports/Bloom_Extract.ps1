# === Bloom_Extract.ps1 (drop in C:\Lattice_Task_Exports\Bloom_Extract.ps1) ===
$roots = @(
  'C:\ProgramData\Bloom_Field_Sovereign',   # 74B anchors
  'C:\ProgramData\Core_Memory_Blooms'       # 162B capsules
) | Where-Object { Test-Path $_ }

$outDir = "C:\Lattice_Task_Exports\Bloom_Map"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$outCsv = Join-Path $outDir ("bloom_map_{0:yyyyMMdd_HHmmss}.csv" -f (Get-Date))

$rows = @()

foreach ($root in $roots) {
  Get-ChildItem -LiteralPath $root -Recurse -File | ForEach-Object {
    $p = $_.FullName
    $size = $_.Length
    $created = $_.CreationTimeUtc
    $modified = $_.LastWriteTimeUtc
    $text = [System.Text.Encoding]::UTF8.GetString([IO.File]::ReadAllBytes($p))

    if ($size -eq 74 -and $text -match '^\[(\d+)\]\s+::\s+(.+?)\s+emitted\s+at\s+([0-9T:\-\.]+)') {
      $id    = $Matches[1]
      $class = $Matches[2].Trim()
      $emit  = $Matches[3]
      $rows += [pscustomobject]@{
        Hub='Sovereign'; Path=$p; Size=$size; ID=$id; Class=$class;
        EmitTime=$emit; CapsuleKey=''; CapsuleVal=''; CreatedUTC=$created; ModifiedUTC=$modified
      }
    }
    elseif ($size -eq 162 -and $text -match '^\[CORE_MEMORY_BLOOM\]') {
      $kv = @{}
      foreach ($line in $text -split "`r?`n") {
        if ($line -match '^\s*([A-Za-z0-9_]+)\s*=\s*(.+)$') { $kv[$Matches[1]] = $Matches[2] }
      }
      $rows += [pscustomobject]@{
        Hub='Core'; Path=$p; Size=$size;
        ID=($kv['bloom_id']); Class='CORE_MEMORY_BLOOM';
        EmitTime=($kv['timestamp']); CapsuleKey='activation_state';
        CapsuleVal=($kv['activation_state']); CreatedUTC=$created; ModifiedUTC=$modified
      }
      if ($kv.ContainsKey('thread_density')) {
        $rows += [pscustomobject]@{
          Hub='Core'; Path=$p; Size=$size;
          ID=($kv['bloom_id']); Class='CORE_MEMORY_BLOOM';
          EmitTime=($kv['timestamp']); CapsuleKey='thread_density';
          CapsuleVal=($kv['thread_density']); CreatedUTC=$created; ModifiedUTC=$modified
        }
      }
      if ($kv.ContainsKey('source_capsule')) {
        $rows += [pscustomobject]@{
          Hub='Core'; Path=$p; Size=$size;
          ID=($kv['bloom_id']); Class='CORE_MEMORY_BLOOM';
          EmitTime=($kv['timestamp']); CapsuleKey='source_capsule';
          CapsuleVal=($kv['source_capsule']); CreatedUTC=$created; ModifiedUTC=$modified
        }
      }
    }
    else {
      # Unknown glyph; log basic facts so we can refine
      $rows += [pscustomobject]@{
        Hub= ( $p -like '*Bloom_Field_Sovereign*' ? 'Sovereign' :
               $p -like '*Core_Memory_Blooms*'    ? 'Core' : 'Other');
        Path=$p; Size=$size; ID=''; Class='?'; EmitTime='';
        CapsuleKey='raw_head'; CapsuleVal=($text.Substring(0,[Math]::Min(64,$text.Length))).Trim();
        CreatedUTC=$created; ModifiedUTC=$modified
      }
    }
  }
}

$rows | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $outCsv
"Bloom map → $outCsv"
