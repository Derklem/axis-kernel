<#
.SYNOPSIS
  Axis Sealer (Hardened): recompute capsule hashes from disk, then seal to ledger with v3 HMAC-SHA256.
.DESCRIPTION
  - Loads Sovereign_State_Capsule.json
  - Recomputes verification.authority_hashes.* from canonical_paths
  - Updates capsule timestamp + last_audit_ts
  - Writes capsule back to disk
  - Appends axis.governance.authority_sync.v3 entry into coin_ledger.jsonl
.NOTES
  Requires coin_secrets.json with one of:
    secrets.hmac_key_b64 OR secrets.hmac_key_hex OR secrets.hmac_key
#>

[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity"
)

$ErrorActionPreference = "Stop"

# --- Paths ---
$Gov     = Join-Path $Root "Governance"
$Runtime = Join-Path $Root "Runtime\Decision"
$CapsulePath = Join-Path $Gov "Sovereign_State_Capsule.json"
$LedgerPath  = Join-Path $Runtime "coin_ledger.jsonl"

function ReadJson([string]$p) {
    if (-not (Test-Path $p)) { throw "Missing JSON: $p" }
    $raw = Get-Content $p -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) { throw "Empty JSON: $p" }
    return ($raw | ConvertFrom-Json)
}

function WriteJson([string]$p, $obj) {
    # Use a stable-ish JSON output; ConvertTo-Json ordering follows insertion order for ordered hashtables,
    # but PSCustomObject property ordering is generally preserved as loaded.
    $json = $obj | ConvertTo-Json -Depth 32
    # Normalize line endings and encoding (UTF8 without BOM)
    [System.IO.File]::WriteAllText($p, $json, (New-Object System.Text.UTF8Encoding($false)))
}

function Sha256Tag([string]$p) {
    if (-not (Test-Path $p)) { return $null }
    "sha256:" + (Get-FileHash -Path $p -Algorithm SHA256).Hash.ToUpper()
}

function HexLower([byte[]]$b) {
    ($b | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Ensure-ByteArray($x) {
    if ($null -eq $x) { return $null }
    if ($x -is [byte[]]) { return $x }
    if ($x -is [string]) { return [System.Text.Encoding]::UTF8.GetBytes($x) }
    try {
        $arr = @($x)
        [byte[]]$b = New-Object byte[] ($arr.Length)
        for ($i=0; $i -lt $arr.Length; $i++) { $b[$i] = [byte]$arr[$i] }
        return $b
    } catch { return $null }
}

function GetKeyBytesFromSecrets($secretsObj) {
    $candidates = @(
        @{ name="hmac_key_b64"; kind="b64" },
        @{ name="hmac_key_hex"; kind="hex" },
        @{ name="hmac_key";     kind="raw" }
    )

    foreach ($c in $candidates) {
        if ($secretsObj -and ($secretsObj.PSObject.Properties.Name -contains $c.name)) {
            $v = [string]$secretsObj.$($c.name)
            if ([string]::IsNullOrWhiteSpace($v)) { continue }

            if ($c.kind -eq "b64") {
                try { return [Convert]::FromBase64String($v) } catch {}
            } elseif ($c.kind -eq "hex") {
                try {
                    $clean = ($v -replace '^0x','' -replace '\s','')
                    if ($clean.Length % 2 -ne 0) { throw "odd hex length" }
                    $bytes = New-Object byte[] ($clean.Length/2)
                    for ($i=0; $i -lt $bytes.Length; $i++) {
                        $bytes[$i] = [Convert]::ToByte($clean.Substring($i*2,2),16)
                    }
                    return $bytes
                } catch {}
            } else {
                return [System.Text.Encoding]::UTF8.GetBytes($v)
            }
        }
    }
    return $null
}

function Hmac256([byte[]]$keyBytes, [string]$msg) {
    if (-not $keyBytes -or $keyBytes.Length -eq 0) { throw "Hmac256: keyBytes empty" }
    $h = [System.Security.Cryptography.HMACSHA256]::new($keyBytes)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $mac = $h.ComputeHash($bytes)
    $h.Dispose()
    return ("hmac256:" + (HexLower $mac))
}

# --- Load capsule ---
$capsule = ReadJson $CapsulePath
if (-not $capsule.canonical_paths) { throw "Capsule missing canonical_paths" }
if (-not $capsule.verification) { throw "Capsule missing verification block" }
if (-not $capsule.verification.authority_hashes) {
    # create if absent
    $capsule.verification | Add-Member -NotePropertyName "authority_hashes" -NotePropertyValue ([pscustomobject]@{}) -Force
}

$paths = $capsule.canonical_paths

# --- Recompute authority hashes from canonical paths ---
$authority = $capsule.verification.authority_hashes

$keys = @()
foreach ($prop in $paths.PSObject.Properties) {
    $name = [string]$prop.Name
    $val  = [string]$prop.Value
    if ([string]::IsNullOrWhiteSpace($name)) { continue }
    if ([string]::IsNullOrWhiteSpace($val)) { continue }
    $keys += $name
}

$missing = @()
foreach ($k in $keys) {
    $diskPath = [string]($paths.$k)
    if (-not (Test-Path $diskPath)) {
        $missing += $k
        continue
    }
    $h = Sha256Tag $diskPath
    $hashProp = ($k + "_sha256")
    # Set/overwrite deterministically
    $authority | Add-Member -NotePropertyName $hashProp -NotePropertyValue $h -Force
}

if ($missing.Count -gt 0) {
    throw ("Sealer refused: missing canonical path targets on disk: " + ($missing -join ", "))
}

# --- Update capsule timestamps ---
$now = (Get-Date).ToUniversalTime().ToString("o")
$capsule.timestamp = $now
$capsule.verification.last_audit_ts = $now

# --- Write capsule back to disk BEFORE signing ---
WriteJson $CapsulePath $capsule

# --- Compute capsule sha after write ---
$capsuleSha = Sha256Tag $CapsulePath

# --- Load secrets & key bytes ---
$secretsPath = $paths.secrets
if (-not $secretsPath) { throw "Capsule canonical_paths.secrets missing" }
$secretsRoot = ReadJson $secretsPath
$secretsObj = $secretsRoot
if ($secretsRoot.PSObject.Properties.Name -contains "secrets") { $secretsObj = $secretsRoot.secrets }

$keyBytes = Ensure-ByteArray (GetKeyBytesFromSecrets $secretsObj)
if (-not $keyBytes -or $keyBytes.Length -eq 0) { throw "Unable to derive HMAC key bytes from coin_secrets.json" }

# --- Construct v3 ledger entry ---
$ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.0000000Z")
$comps = @($paths.PSObject.Properties.Name | Sort-Object)
$sorted = $comps -join ","
$msg = "$ts|$capsuleSha|$sorted"
$sig = Hmac256 $keyBytes $msg

$entry = [ordered]@{
    ts = $ts
    decision = "AUTHORITY_SYNC"
    schema = "axis.governance.authority_sync.v3"
    capsule_sha256 = $capsuleSha
    rebound_components = $comps
    signature = $sig
}

# --- Append to ledger (UTF8 no BOM) ---
if (-not (Test-Path $LedgerPath)) {
    # Create empty if missing
    [System.IO.File]::WriteAllText($LedgerPath, "", (New-Object System.Text.UTF8Encoding($false)))
}
$line = ($entry | ConvertTo-Json -Compress)
[System.IO.File]::AppendAllText($LedgerPath, $line + "`n", (New-Object System.Text.UTF8Encoding($false)))

Write-Host ("[PASS] Capsule updated + sealed. capsule_sha={0} ts={1}" -f $capsuleSha, $ts) -ForegroundColor Green
