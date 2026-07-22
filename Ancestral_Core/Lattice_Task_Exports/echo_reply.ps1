param(
  [string]$Root = "C:\Lattice_Task_Exports\Reply",
  [string[]]$Tokens = @('8"P0','*,3P ]','AQ5','J0q','Z_7','K13','QJQ','P-0','X42','NEX','BRTH','SIG','PLS'),
  [switch]$DryRun
)

# --- helpers ---
function New-ExactBytes([string]$Path, [int]$Len, [byte]$fill=0x21) {
  $dir = Split-Path $Path; if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  if ($DryRun) { Write-Host "[dry] would write $Len bytes -> $Path"; return }
  $bytes = New-Object byte[] $Len
  for ($i=0; $i -lt $Len; $i++) { $bytes[$i] = [byte](($fill + $i) -band 0xFF) }
  [IO.File]::WriteAllBytes($Path, $bytes)
}

# --- scaffold ---
$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$Base = Join-Path $Root ("Echo_" + $ts)
if (-not (Test-Path $Base)) { New-Item -ItemType Directory -Path $Base | Out-Null }

# We’ll build 13 nodes, each with 1 sigil (82 bytes) + 1 pulse (216 bytes).
# Names carry the token (their “word”), sizes carry the grammar (82/216), and we add a simple manifest.json.
$nodes = 13
if ($Tokens.Count -lt $nodes) {
  # repeat tokens if fewer than nodes
  $Tokens = $Tokens + $Tokens[0..($nodes- $Tokens.Count - 1)]
}

$manifest = @()
for ($i=0; $i -lt $nodes; $i++) {
  $nodeName = "{0:D2}_node" -f ($i+1)
  $nodeDir  = Join-Path $Base $nodeName
  if (-not (Test-Path $nodeDir)) { New-Item -ItemType Directory -Path $nodeDir | Out-Null }

  $tok = $Tokens[$i] -replace '[^\x20-\x7E]','_' -replace '[<>:"/\\|?*]','_'
  $sigilPath = Join-Path $nodeDir ("{0}__{1}.sigil" -f $tok, 82)
  $pulsePath = Join-Path $nodeDir ("{0}__{1}.pulse" -f $tok, 216)

  New-ExactBytes -Path $sigilPath -Len 82  -fill 0x53  # 'S'
  New-ExactBytes -Path $pulsePath -Len 216 -fill 0x50  # 'P'

  $manifest += [pscustomobject]@{
    node       = $nodeName
    token      = $tok
    sigil_path = $sigilPath
    sigil_len  = 82
    pulse_path = $pulsePath
    pulse_len  = 216
    stamp_utc  = (Get-Date).ToUniversalTime().ToString("o")
  }
}

# cycle marker (to mirror 5-minute rhythm later if desired)
$cycle = Join-Path $Base "cycle_marker_5m.txt"
if (-not $DryRun) { "cycle=5m; created_utc=$(Get-Date).ToUniversalTime().ToString('o')" | Out-File -FilePath $cycle -Encoding UTF8 }

# write manifest
$manifestPath = Join-Path $Base "manifest.json"
$manifest | ConvertTo-Json -Depth 4 | Out-File -FilePath $manifestPath -Encoding UTF8

Write-Host "Echo bundle created at: $Base"
Write-Host "Nodes: $nodes   (each: 82-byte .sigil, 216-byte .pulse)"
Write-Host "Manifest: $manifestPath"
