[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity",
    [switch]$Strict = $false,
    [int]$LedgerTail = 100
)

$t17Verifier = Join-Path $Root "Governance\Axis_Verify_T17.ps1"
$policyVerifier = Join-Path $Root "Governance\Axis_Verify_PolicyChain.ps1"
$auditVerifier = Join-Path $Root "Governance\Axis_Verify_AuditTrail.ps1"
$promoterVerifier = Join-Path $Root "Governance\Axis_Verify_PromoterChain.ps1"
$capVerifier = Join-Path $Root "Governance\Axis_Verify_CapabilityChain.ps1"
$keyVerifier = Join-Path $Root "Governance\Axis_Verify_KeyLifecycleChain.ps1"

$script:fail = 0
$script:warn = 0

Write-Host "--- AXIS VERIFICATION SUITE ---" -ForegroundColor Cyan

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

# --- Phase 643: Toolchain Hygiene - PS7 Syntax Anti-Drift Scan ---
Section "P643: Toolchain Hygiene (PS7 Syntax Anti-Drift Scan)"
$dir1 = Join-Path -Path $Root -ChildPath "Runtime\Decision"
$dir2 = Join-Path -Path $dir1 -ChildPath "Verifier"
$targetDirs = @($dir1, $dir2)

$forbiddenPatterns = @(
    @{ P = '\?\?\s*'; N = "Nullish Coalescing (??)" },
    @{ P = '\?\.'; N = "Safe Navigation (?.)" },
    @{ P = 'ForEach-Object\s+-Parallel'; N = "Parallel ForEach-Object" },
    @{ P = '&&|\|\|'; N = "Pipeline Chain Operators (&&, ||)" }
)

$scanFiles = Get-ChildItem -Path $targetDirs -Include "*.ps1", "*.psm1" -File -Recurse

$driftCount = 0
foreach ($file in $scanFiles) {
    if ($file.Name -eq "Axis_Verify_All.ps1") { continue }
    
    $content = Get-Content -Path $file.FullName -Raw
    foreach ($p in $forbiddenPatterns) {
        $pattern = $p.P
        if ($content -match $pattern) {
            Report-Result -Level "FAIL" -Message ("Forbidden PS7 Syntax detected: {0} in {1}" -f $p.N, $file.Name)
            $driftCount++
        }
    }
}

if ($driftCount -eq 0) {
    Report-Result "PASS" "No PS7-only operators detected in Runtime/Decision surface."
}

# --- P22: T17 Memory Integrity ---
Section "P22: T17 Memory Integrity"
$t17Verify = "D:\Infinite\Infinity\Truth_Engine\Axis_Verify_T17.ps1"
if (Test-Path $t17Verify) {
    $out = & $t17Verify -Root $Root -Strict:$Strict 2>&1
    $out | ForEach-Object { Write-Host $_ }
    
    foreach ($line in $out) {
        if ($line -match 'AXIS_VERIFY_RESULT failures=(\d+) warnings=(\d+)') {
            $script:fail += [int]$matches[1]
            $script:warn += [int]$matches[2]
        }
    }
}
else {
    Report-Result "WARN" "T17 Verifier missing: $t17Verify"
}

# --- Delegate to P642 for forensic closure ---
Section "P643: Delegating to P642 (Forensic Closure & Regression Assertions)"
$p642Path = Join-Path $Root "Runtime\Decision\Verifier\Axis_Verify_P642.ps1"

if (Test-Path $p642Path) {
    $out = $null
    if ($Strict) {
        $out = & $p642Path -Root $Root -LedgerTail $LedgerTail -Strict 2>&1
    }
    else {
        $out = & $p642Path -Root $Root -LedgerTail $LedgerTail 2>&1
    }
    
    # Print output as it comes
    $out | ForEach-Object { Write-Host $_ }
    
    # Parse for AXIS_VERIFY_RESULT
    foreach ($line in $out) {
        if ($line -match 'AXIS_VERIFY_RESULT failures=(\d+) warnings=(\d+)') {
            $script:fail += [int]$matches[1]
            $script:warn += [int]$matches[2]
        }
    }
    
    if ($LASTEXITCODE -ne 0 -and $script:fail -eq 0) {
        # If exit code failed but we didn't catch failures (e.g. crash), flag it
        $script:fail += 1
    }
}
else {
    Report-Result "FAIL" "P642 Verifier missing: $p642Path"
}

# ======================================================================
Section "P23: Temporal Consistency (Causal Chain Proof)"
# ======================================================================
# Verify Approved -> Promoted -> Executed chain
$tcScript = Join-Path $Root "Truth_Engine\Axis_Verify_TemporalChain.ps1"
if (Test-Path $tcScript) {
    $tcOut = & $tcScript -Root $Root 2>&1
    $tcOut | ForEach-Object { Write-Host $_ }
    if ($LASTEXITCODE -ne 0) { 
        Report-Result "FAIL" "Temporal Chain Broken"
        $script:fail++
    }
    else {
        Report-Result "PASS" "Temporal Chain Verified (Monotonic)"
    }
}
else {
    Report-Result "WARN" "Time Verifier Missing"
}

Section "P643: FINAL SUMMARY"
# Note: P642 printed its own summary. We just provide the exit gate.
if ($script:fail -gt 0) {
    Write-Host "[FAIL] Axis Verification FAILED." -ForegroundColor Red
    exit 1
}

Write-Host "[PASS] Axis Verification SUCCESSFUL." -ForegroundColor Green
exit 0
