param(
    [string]$Root = "D:\Infinite\Infinity",
    [int]$LedgerTail = 2000,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"
$script:fail = 0
$script:warn = 0

function Set-Section($t) {
    Write-Host "`n"
    Write-Host ("="*70) -ForegroundColor DarkGray
    Write-Host $t -ForegroundColor Cyan
    Write-Host ("="*70) -ForegroundColor DarkGray
}

function Report-Result($lvl, $msg) {
    if ($lvl -eq "PASS") { Write-Host "[PASS] $msg" -ForegroundColor Green }
    elseif ($lvl -eq "FAIL") { Write-Host "[FAIL] $msg" -ForegroundColor Red; $script:fail++ }
    elseif ($lvl -eq "WARN") { Write-Host "[WARN] $msg" -ForegroundColor Yellow; $script:warn++ }
    else { Write-Host "[$lvl] $msg" -ForegroundColor Gray }
}

function Read-Json($p) {
    if (-not (Test-Path $p)) { throw "Missing JSON: $p" }
    $raw = Get-Content $p -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) { throw "Empty JSON: $p" }
    return ($raw | ConvertFrom-Json)
}

function Get-Sha256Tag($p) {
    if (-not (Test-Path $p)) { return $null }
    $h = Get-FileHash -Path $p -Algorithm SHA256
    return ("sha256:" + $h.Hash.ToUpper())
}

function Get-HexLower($b) {
    $s = ""
    foreach($x in $b) { $s += $x.ToString("x2") }
    return $s
}

function Get-Hmac256($keyBytes, $msg) {
    $h = [System.Security.Cryptography.HMACSHA256]::new($keyBytes)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $mac = $h.ComputeHash($bytes)
    $h.Dispose()
    return ("hmac256:" + (Get-HexLower $mac))
}

function Get-KeyBytesFromSecrets($sObj) {
    if (-not $sObj) { return $null }

    # priority: b64 -> hex -> raw
    if ($sObj.PSObject.Properties.Name -contains "hmac_key_b64") {
        $v = [string]$sObj.hmac_key_b64
        if (-not [string]::IsNullOrWhiteSpace($v)) {
            try { return ,([Convert]::FromBase64String($v)) } catch {}
        }
    }

    if ($sObj.PSObject.Properties.Name -contains "hmac_key_hex") {
        $v = [string]$sObj.hmac_key_hex
        if (-not [string]::IsNullOrWhiteSpace($v)) {
            try {
                $clean = ($v -replace '^0x','' -replace '\s','')
                if ($clean.Length % 2 -ne 0) { throw "odd hex length" }
                $bytes = New-Object byte[] ($clean.Length/2)
                for ($i=0; $i -lt $bytes.Length; $i++) {
                    $bytes[$i] = [Convert]::ToByte($clean.Substring($i*2,2),16)
                }
                return ,$bytes
            } catch {}
        }
    }

    if ($sObj.PSObject.Properties.Name -contains "hmac_key") {
        $v = [string]$sObj.hmac_key
        if (-not [string]::IsNullOrWhiteSpace($v)) {
            return ,([System.Text.Encoding]::UTF8.GetBytes($v))
        }
    }

    return $null
}

function Find-CapsuleKey($pathsObj, [string[]]$tokens) {
    foreach ($p in $pathsObj.PSObject.Properties) {
        $n = $p.Name.ToLower()
        foreach ($t in $tokens) {
            if ($n -like "*$t*") { return $p.Name }
        }
    }
    return $null
}

function Coalesce([object]$value, [object]$fallback) {
    if ($null -eq $value -or ([string]$value).Trim().Length -eq 0) { return $fallback }
    return $value
}

function Check-Binding($pathsObj, $hashesObj, [string]$key, [string]$label) {
    if ([string]::IsNullOrWhiteSpace($key)) { Report-Result "FAIL" "$label key not resolved from capsule"; return $null }

    $p = [string]$pathsObj.$key
    if ([string]::IsNullOrWhiteSpace($p)) { Report-Result "FAIL" "Key $key missing/empty in canonical_paths"; return $null }

    $hashProp = $key + "_sha256"
    $exp = [string]$hashesObj.$hashProp
    if ([string]::IsNullOrWhiteSpace($exp)) { Report-Result "FAIL" "Hash for $key missing ($hashProp)"; return $p }

    Report-Result "PASS" "Capsule binds $label (key=$key)"
    if (Test-Path $p) {
        if ((Get-Sha256Tag $p) -eq $exp) { Report-Result "PASS" "Integrity OK: $label" }
        else { Report-Result "FAIL" "SHA256 MISMATCH: $label" }
    } else {
        Report-Result "FAIL" "File missing: $p"
    }

    return $p
}

$Gov = Join-Path $Root "Governance"
$Runtime = Join-Path $Root "Runtime\Decision"
$CapsulePath = Join-Path $Gov "Sovereign_State_Capsule.json"
$LedgerPath  = Join-Path $Runtime "coin_ledger.jsonl"

Set-Section "PHASE 640 FULL PROOF: Surface Files"
if (Test-Path $CapsulePath) { Report-Result "PASS" "Capsule exists" } else { Report-Result "FAIL" "Capsule missing" }
if (Test-Path $LedgerPath)  { Report-Result "PASS" "Ledger exists" } else { Report-Result "FAIL" "Ledger missing" }

$capsule = $null
try { $capsule = Read-Json $CapsulePath } catch { Report-Result "FAIL" $_.Exception.Message }
if (-not $capsule) { exit 2 }

$paths = $capsule.canonical_paths
$hashes = $capsule.verification.authority_hashes

Set-Section "PHASE 640 FULL PROOF: Resolve Keys (Capsule-driven)"
$kSecrets = Find-CapsuleKey $paths @("secret")
$kEgress  = Find-CapsuleKey $paths @("egress")
$kNorm    = Find-CapsuleKey $paths @("normal")
$kTarget  = Find-CapsuleKey $paths @("target","resolver")
$kExec    = $null
if ($paths.PSObject.Properties.Name -contains "executor") { $kExec = "executor" } else { $kExec = Find-CapsuleKey $paths @("t08","executor") }

Report-Result "INFO" ("secrets key=" + (Coalesce $kSecrets "<none>"))
Report-Result "INFO" ("egress key =" + (Coalesce $kEgress  "<none>"))
Report-Result "INFO" ("normal key =" + (Coalesce $kNorm    "<none>"))
Report-Result "INFO" ("target key =" + (Coalesce $kTarget  "<none>"))
Report-Result "INFO" ("exec key   =" + (Coalesce $kExec    "<none>"))

Set-Section "PHASE 640 FULL PROOF: Binding Check"
$secretsPath = Check-Binding $paths $hashes $kSecrets "secrets"
$null = Check-Binding $paths $hashes $kEgress  "egress_gate"
$null = Check-Binding $paths $hashes $kNorm    "normalizer"
$null = Check-Binding $paths $hashes $kTarget  "target_resolver"

Set-Section "PHASE 640 FULL PROOF: Signature Check"
$checked = 0; $bad = 0
if ($secretsPath -and (Test-Path $secretsPath)) {
    try {
        $sRoot = Read-Json $secretsPath
        $sObj = $sRoot
        if ($sRoot.PSObject.Properties.Name -contains "secrets") { $sObj = $sRoot.secrets }

        $kB = Get-KeyBytesFromSecrets $sObj
        if (-not $kB) {
            Report-Result "FAIL" "Could not derive HMAC key bytes (expected hmac_key_b64 OR hmac_key_hex OR hmac_key)."
        } else {
            $actualCapHash = Get-Sha256Tag $CapsulePath
            Report-Result "INFO" ("On-disk Capsule Hash: " + $actualCapHash)
            
            $lines = @()
            try { $lines = Get-Content $LedgerPath -Tail $LedgerTail } catch { $lines = Get-Content $LedgerPath }

            foreach ($ln in $lines) {
                if ([string]::IsNullOrWhiteSpace($ln)) { continue }
                $o = $null; try { $o = $ln | ConvertFrom-Json } catch { continue }
                if ($o.schema -eq "axis.governance.authority_sync.v3" -and $o.signature -and $o.ts -and $o.capsule_sha256 -and $o.rebound_components) {
                    $checked++
                    $comps = @(); foreach($c in $o.rebound_components) { $comps += [string]$c }
                    $msg = "$($o.ts)|$($o.capsule_sha256)|$(($comps|Sort-Object)-join ',')"
                    if ((Get-Hmac256 $kB $msg) -eq [string]$o.signature) { 
                        if ($o.capsule_sha256 -eq $actualCapHash) {
                            Report-Result "PASS" ("v3 Sig OK + Capsule Hash Match (ts=" + $o.ts + ")")
                        } else {
                            $bad++; Report-Result "FAIL" ("v3 Sig OK but Capsule Hash MISMATCH (ts=" + $o.ts + ")")
                            Write-Host ("  Ledger: " + $o.capsule_sha256)
                            Write-Host ("  Disk:   " + $actualCapHash)
                        }
                    } else { $bad++; Report-Result "FAIL" ("v3 Sig FAIL at " + $o.ts) }
                }
            }

            Report-Result "INFO" "Checked $checked v3 entries (bad=$bad)"
            if ($Strict -and $checked -eq 0) { Report-Result "FAIL" "Strict: No v3 signed entries found in tail window." }
        }
    } catch { Report-Result "FAIL" $_.Exception.Message }
} else {
    Report-Result "FAIL" "Secrets path invalid"
}

Set-Section "PHASE 640 FULL PROOF: Sentinel Check"
try {
    $exP = $null
    if ($kExec) { $exP = [string]$paths.$kExec }

    if (-not $exP -or -not (Test-Path $exP)) { Report-Result "FAIL" "Executor path missing/unresolved" }
    else {
        $txt = Get-Content $exP
        $cIdx = @(); $eIdx = @()
        for($i=0; $i -lt $txt.Count; $i++) {
            if ($txt[$i] -match '^\s*&\s*\$Client\b') { $cIdx += $i }
            if ($txt[$i] -match '^\s*\$result\s*=\s*&\s*\$cmdlet\b' -or $txt[$i] -match '^\s*&\s*\$cmdlet\b') { $eIdx += $i }
        }

        function Window-Has-Sentinel($idx) {
            $start = [Math]::Max(0, $idx-60)
            $win = ($txt[$start..$idx] -join "`n")
            return ($win -match "OBSERVATION_ONLY") -and ($win -match "\b(return|continue|throw|BLOCK)\b")
        }

        if ($cIdx.Count -eq 0) { Report-Result "WARN" "No '& `$Client' call site found (maybe renamed)." }
        foreach($idx in $cIdx) {
            if (Window-Has-Sentinel $idx) { Report-Result "PASS" "Client point-of-impact sentinel found" }
            else { Report-Result "FAIL" "Client sentinel MISSING near line $($idx+1)" }
        }

        if ($eIdx.Count -eq 0) { Report-Result "WARN" "No '& `$cmdlet' Earth call site found (maybe refactored)." }
        foreach($idx in $eIdx) {
            if (Window-Has-Sentinel $idx) { Report-Result "PASS" "Earth point-of-impact sentinel found" }
            else { Report-Result "FAIL" "Earth sentinel MISSING near line $($idx+1)" }
        }
    }
} catch { Report-Result "FAIL" $_.Exception.Message }

Set-Section "SUMMARY"
if ($Strict -and $script:warn -gt 0) { Report-Result "FAIL" ("Strict: warnings present (warnings=" + $script:warn + ")"); $script:fail++ }

if ($script:fail -gt 0) { Write-Host "FAILED" -ForegroundColor Red; exit 2 }
elseif ($script:warn -gt 0) { Write-Host "PASSED WITH WARNINGS" -ForegroundColor Yellow; exit 1 }
else { Write-Host "PASSED" -ForegroundColor Green; exit 0 }
