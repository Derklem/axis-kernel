[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity",
    [int]$LedgerTail = 4000,
    [switch]$Strict
)

$ErrorActionPreference = "Stop"

$script:fail = 0
$script:warn = 0

function Section([string]$t) {
    Write-Host ""
    Write-Host ("=" * 70) -ForegroundColor DarkGray
    Write-Host $t -ForegroundColor Cyan
    Write-Host ("=" * 70) -ForegroundColor DarkGray
}

function Report-Result([string]$Level, [string]$Message) {
    switch ($Level) {
        "PASS" { Write-Host "[PASS] $Message" -ForegroundColor Green }
        "FAIL" { Write-Host "[FAIL] $Message" -ForegroundColor Red; $script:fail++ }
        "WARN" { Write-Host "[WARN] $Message" -ForegroundColor Yellow; $script:warn++ }
        "INFO" { Write-Host "[INFO] $Message" -ForegroundColor Gray }
        default { Write-Host "[$Level] $Message" -ForegroundColor Gray }
    }
}

function Fail-IfStrict([string]$Message) {
    if ($Strict) { Report-Result "FAIL" $Message } else { Report-Result "WARN" $Message }
}

function ReadJson([string]$p) {
    if (-not (Test-Path $p)) { throw "Missing JSON: $p" }
    $raw = Get-Content $p -Raw
    if ([string]::IsNullOrWhiteSpace($raw)) { throw "Empty JSON: $p" }
    return ($raw | ConvertFrom-Json)
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
        for ($i = 0; $i -lt $arr.Length; $i++) { $b[$i] = [byte]$arr[$i] }
        return $b
    }
    catch {
        return $null
    }
}

function Hmac256([byte[]]$keyBytes, [string]$msg) {
    if (-not $keyBytes -or $keyBytes.Length -eq 0) { throw "Hmac256: keyBytes empty" }
    $h = [System.Security.Cryptography.HMACSHA256]::new($keyBytes)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($msg)
    $mac = $h.ComputeHash($bytes)
    $h.Dispose()
    return ("hmac256:" + (HexLower $mac))
}

function GetKeyBytesFromSecrets($secretsObj) {
    $candidates = @(
        @{ name = "hmac_key_b64"; kind = "b64" },
        @{ name = "hmac_key_hex"; kind = "hex" },
        @{ name = "hmac_key"; kind = "raw" }
    )

    foreach ($c in $candidates) {
        if ($secretsObj -and ($secretsObj.PSObject.Properties.Name -contains $c.name)) {
            $v = [string]$secretsObj.$($c.name)
            if ([string]::IsNullOrWhiteSpace($v)) { continue }

            if ($c.kind -eq "b64") {
                try { return [Convert]::FromBase64String($v) } catch {}
            }
            elseif ($c.kind -eq "hex") {
                try {
                    $clean = ($v -replace '^0x', '' -replace '\s', '')
                    if ($clean.Length % 2 -ne 0) { throw "odd hex length" }
                    $bytes = New-Object byte[] ($clean.Length / 2)
                    for ($i = 0; $i -lt $bytes.Length; $i++) {
                        $bytes[$i] = [Convert]::ToByte($clean.Substring($i * 2, 2), 16)
                    }
                    return $bytes
                }
                catch {}
            }
            else {
                return [System.Text.Encoding]::UTF8.GetBytes($v)
            }
        }
    }
    return $null
}

# --- Paths ---
$Gov = Join-Path $Root "Governance"
$Runtime = Join-Path $Root "Runtime\Decision"
$CapsulePath = Join-Path $Gov "Sovereign_State_Capsule.json"
$LedgerPath = Join-Path $Runtime "coin_ledger.jsonl"

# --- P24: Policy Integrity ---
Section "P24: Policy Integrity (Hardened v2)"
$verifierPolicy = Join-Path $Gov "Axis_Verify_PolicyChain.ps1"
$ledgerV2 = Join-Path $Gov "policy_update_ledger_v2.jsonl"
$ledgerV1 = Join-Path $Gov "policy_update_ledger.jsonl"

if (Test-Path $verifierPolicy) {
    if (Test-Path $ledgerV2) {
        Report-Result "INFO" "Validating v2 Ledger: $ledgerV2"
        # Note: VerifyRuntime defaults to true in script, we can pass it if we want full check
        # For 'All' verification, we usually want runtime binding check.
        $out = & $verifierPolicy -LedgerPath $ledgerV2 2>&1
    }
    else {
        Report-Result "WARN" "v2 Ledger missing, falling back to v1"
        $out = & $verifierPolicy -LedgerPath $ledgerV1 2>&1
    }
    
    $out | ForEach-Object { Write-Host "  $_" } # Indent for readability
    
    # Simple scrape for PASS
    if ($LASTEXITCODE -ne 0) {
        $script:fail++ 
        Report-Result "FAIL" "Policy Verification Failed"
    }
    else {
        Report-Result "PASS" "Policy Chain Integrity OK"
    }
}
else {
    Report-Result "FAIL" "Policy Verifier missing"
}

# --- P642: Surface Files (Original Section) ---
Section "P642: Surface Files"
if (Test-Path $CapsulePath) { Report-Result "PASS" "Capsule exists" } else { Report-Result "FAIL" "Capsule missing: $CapsulePath" }
if (Test-Path $LedgerPath) { Report-Result "PASS" "Ledger exists" } else { Fail-IfStrict "Ledger missing: $LedgerPath" }

# Load capsule
$capsule = $null
try { $capsule = ReadJson $CapsulePath } catch { Report-Result "FAIL" $_.Exception.Message }
if (-not $capsule) {
    Section "SUMMARY"
    Report-Result "INFO" ("failures={0} warnings={1} strict={2}" -f $script:fail, $script:warn, [bool]$Strict)
    exit 1
}

$paths = $capsule.canonical_paths
$hashes = $capsule.verification.authority_hashes

Section "P642: Hash Verification"
$compKeys = @(
    "executor", "constraints", "contract", "coin_protocol",
    "run_t08", "system_mode",
    "normalizer", "egress_gate", "secrets", "target_resolver"
)

foreach ($k in $compKeys) {
    try {
        $pProp = $paths.PSObject.Properties | Where-Object { $_.Name -eq $k } | Select-Object -First 1
        if (-not $pProp) { Report-Result "FAIL" "Missing path for $k"; continue }
        $diskPath = [string]$pProp.Value

        $hProp = $hashes.PSObject.Properties | Where-Object { $_.Name -eq ($k + "_sha256") } | Select-Object -First 1
        if (-not $hProp) { Report-Result "FAIL" "Missing hash for $k"; continue }
        $expHash = [string]$hProp.Value

        if (-not (Test-Path $diskPath)) { Report-Result "FAIL" "File missing: $diskPath"; continue }

        $actHash = Sha256Tag $diskPath
        if ($actHash -eq $expHash) {
            Report-Result "PASS" "Integrity OK: $k"
        }
        else {
            Report-Result "FAIL" "Hash Mismatch: $k"
            Report-Result "INFO" ("  Exp: {0}" -f $expHash)
            Report-Result "INFO" ("  Act: {0}" -f $actHash)
        }
    }
    catch {
        Report-Result "FAIL" ("Exception verifying {0}: {1}" -f $k, $_.Exception.Message)
    }
}

Section "P642: v3 Signature Proof (ts|capsule_sha256|sorted_components)"
$didV3 = $false

try {
    if (-not (Test-Path $LedgerPath)) {
        Fail-IfStrict "Ledger absent: cannot verify v3 signatures."
        $didV3 = $true
    }
    else {
        $secretsPathProp = $paths.PSObject.Properties | Where-Object { $_.Name -eq "secrets" } | Select-Object -First 1
        if (-not $secretsPathProp) {
            Fail-IfStrict "Capsule has no canonical_paths.secrets"
            $didV3 = $true
        }
        else {
            $secretsPath = [string]$secretsPathProp.Value
            if (-not (Test-Path $secretsPath)) {
                Fail-IfStrict "Secrets file missing on disk: $secretsPath"
                $didV3 = $true
            }
            else {
                $secretsRoot = ReadJson $secretsPath
                $secretsObj = $secretsRoot
                if ($secretsRoot.PSObject.Properties.Name -contains "secrets") { $secretsObj = $secretsRoot.secrets }

                $keyBytesRaw = GetKeyBytesFromSecrets $secretsObj
                $keyBytes = Ensure-ByteArray $keyBytesRaw
                if (-not $keyBytes -or $keyBytes.Length -eq 0) {
                    Fail-IfStrict "Unable to derive HMAC key bytes from coin_secrets.json"
                    $didV3 = $true
                }
                else {
                    Report-Result "PASS" "Derived HMAC key bytes (not displayed)."
                    Report-Result "INFO" ("HMAC key length: {0} bytes" -f $keyBytes.Length)

                    $capsuleSha = Sha256Tag $CapsulePath
                    Report-Result "INFO" ("Capsule sha256 (disk): {0}" -f $capsuleSha)

                    $lines = @()
                    try { $lines = @(Get-Content $LedgerPath -Tail $LedgerTail) } catch { $lines = @(Get-Content $LedgerPath) }

                    $latestTs = $null
                    $latestObj = $null
                    $latestSigOk = $false
                    $latestCapMatch = $false

                    foreach ($ln in $lines) {
                        if ([string]::IsNullOrWhiteSpace($ln)) { continue }
                        $obj = $null
                        try { $obj = $ln | ConvertFrom-Json } catch { continue }
                        if (-not $obj) { continue }

                        if ($obj.schema -eq "axis.governance.authority_sync.v3" -and $obj.signature -and $obj.capsule_sha256 -and $obj.ts -and $obj.rebound_components) {
                            $tsObj = $null
                            try { $tsObj = [DateTimeOffset]::Parse([string]$obj.ts) } catch { $tsObj = $null }

                            $ts = [string]$obj.ts
                            $capHash = [string]$obj.capsule_sha256

                            $comps = @()
                            foreach ($c in $obj.rebound_components) { $comps += [string]$c }
                            $sorted = ($comps | Sort-Object) -join ","
                            $msg = ($ts + "|" + $capHash + "|" + $sorted)

                            $calc = Hmac256 $keyBytes $msg
                            $sig = [string]$obj.signature
                            $sigOk = ($calc -eq $sig)
                            $capOk = ($capHash -eq $capsuleSha)

                            if ($tsObj) {
                                if (-not $latestTs -or $tsObj -gt $latestTs) {
                                    $latestTs = $tsObj
                                    $latestObj = $obj
                                    $latestSigOk = $sigOk
                                    $latestCapMatch = $capOk
                                }
                            }

                            if (-not $sigOk) {
                                Report-Result "FAIL" ("v3 Sig FAIL (ts={0})" -f $ts)
                            }
                        }
                    }

                    if (-not $latestObj) {
                        Fail-IfStrict "No v3 authority_sync entries found in last $LedgerTail lines."
                    }
                    elseif (-not $latestSigOk) {
                        Fail-IfStrict ("Latest v3 entry signature FAIL (ts={0})" -f $latestObj.ts)
                    }
                    elseif (-not $latestCapMatch) {
                        Fail-IfStrict ("Latest v3 entry capsule hash does NOT match disk capsule (ts={0})" -f $latestObj.ts)
                        Report-Result "INFO" ("  ledger: {0}" -f $latestObj.capsule_sha256)
                        Report-Result "INFO" ("  disk:   {0}" -f $capsuleSha)
                    }
                    else {
                        Report-Result "PASS" ("Latest v3 entry matches disk capsule (ts={0})" -f $latestObj.ts)
                    }

                    $didV3 = $true
                }
            }
        }
    }
}
catch {
    Fail-IfStrict ("v3 proof crashed: {0}" -f $_.Exception.Message)
    $didV3 = $true
}

if (-not $didV3) {
    Fail-IfStrict "v3 proof did not run (unexpected control flow)."
}

Section "P642: Regression Assertions"
try {
    $execPath = [string]$paths.executor
    if (-not $execPath -or -not (Test-Path $execPath)) {
        Report-Result "FAIL" "Executor path missing/unreadable"
    }
    else {
        $txt = Get-Content $execPath
        $joined = $txt -join "`n"

        $earlyReturn = $false
        if ($joined -match '\[OBSERVER\][\s\S]{0,300}return') { $earlyReturn = $true }
        if ($joined -match 'Skipping Actuation[\s\S]{0,200}return') { $earlyReturn = $true }
        if ($joined -match 'System in .*OBSERVATION_ONLY[\s\S]{0,300}return') { $earlyReturn = $true }

        if ($earlyReturn) { Report-Result "FAIL" "Detected early-return in OBSERVATION_ONLY mode (Queue pile-up risk)" }
        else { Report-Result "PASS" "No early-return regression detected" }

        $clientHits = 0; $earthHits = 0
        $clientSents = 0; $earthSents = 0

        for ($i = 0; $i -lt $txt.Count; $i++) {
            if ($txt[$i] -match '&\s*\$Client\b') {
                $clientHits++
                $start = [Math]::Max(0, $i - 40)
                $win = $txt[$start..$i] -join " "
                if ($win -match "OBSERVATION_ONLY") { $clientSents++ }
            }
            if ($txt[$i] -match '&\s*\$cmdlet\b') {
                $earthHits++
                $start = [Math]::Max(0, $i - 40)
                $win = $txt[$start..$i] -join " "
                if ($win -match "OBSERVATION_ONLY") { $earthSents++ }
            }
        }

        if ($clientHits -gt 0) {
            if ($clientHits -eq $clientSents) { Report-Result "PASS" ("Client sentinels present ({0}/{1})" -f $clientSents, $clientHits) }
            else { Report-Result "FAIL" ("Client sentinels missing ({0}/{1} hits)" -f $clientSents, $clientHits) }
        }
        else { Report-Result "WARN" "No & `$Client invocation sites found." }

        if ($earthHits -gt 0) {
            if ($earthHits -eq $earthSents) { Report-Result "PASS" ("Earth sentinels present ({0}/{1})" -f $earthSents, $earthHits) }
            else { Report-Result "FAIL" ("Earth sentinels missing ({0}/{1} hits)" -f $earthSents, $earthHits) }
        }
        else { Report-Result "WARN" "No & `$cmdlet invocation sites found." }
    }
}
catch {
    Report-Result "FAIL" ("Regression assertion step crashed: {0}" -f $_.Exception.Message)
}

Section "SUMMARY"
Report-Result "INFO" ("failures={0} warnings={1} strict={2}" -f $script:fail, $script:warn, [bool]$Strict)
Write-Host ("AXIS_VERIFY_RESULT failures={0} warnings={1}" -f $script:fail, $script:warn)

if ($script:fail -gt 0) { exit 1 }
if ($Strict -and $script:warn -gt 0) { exit 1 }
exit 0
