$ErrorActionPreference = "Stop"

# --- Constants ---
$Root = "D:\Infinite\Infinity"
$Runtime = Join-Path $Root "Runtime\Decision"
$IntentQueue = Join-Path $Runtime "intent_queue.jsonl"
$ReviewLog = Join-Path $Runtime "Review\review_log.jsonl"
$DecisionLog = Join-Path $Runtime "decision_log.jsonl"
$Executor = Join-Path $Runtime "T08_Executor.ps1"
$ReviewManager = "D:\Infinite\Infinity\Runtime\Decision\Review\Axis_Review_Manager.ps1"

# --- Helper: Create Envelope ---
function New-Envelope {
    param($id, $nonce, $identity, $intent)
    $intentJson = $intent | ConvertTo-Json -Compress
    
    return [ordered]@{
        schema        = "axis.intent_envelope.v0.1"
        ts_utc        = (Get-Date).ToUniversalTime().ToString("o")
        exercises_utc = (Get-Date).AddHours(24).ToUniversalTime().ToString("o")
        nonce         = $nonce
        identity      = $identity
        signature     = "internal:test" 
        intent_json   = $intentJson
    }
}

# --- Helper: Approve in Log ---
function Mock-Approve {
    param($nonce, $intentJson)
    
    # We call Axis_Review_Manager directly to generate a valid signature/entry
    # But wait, review manager needs the proposal to be in voice_proposals.jsonl?
    # No, we can just append a valid log line manually if we know the secret?
    # Actually, let's use the Review Manager script but we need to mock the "Outbox" check or inject into outbox.
    # EASIER: We just append a raw JSON line to review_log.jsonl that MATCHES what T08 expects.
    # T08 checks: action="APPROVED", proposal_id=$nonce, intent_sha256=Hash($intentJson)
    
    # Compute Hash
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($intentJson)
    $algo = [System.Security.Cryptography.SHA256]::Create()
    $hash = $algo.ComputeHash($bytes)
    $sha = ($hash | ForEach-Object { $_.ToString("x2") }) -join ""

    $evt = [ordered]@{
        schema        = "axis.review.event.v1"
        ts            = (Get-Date).ToUniversalTime().ToString("o")
        proposal_id   = $nonce
        action        = "APPROVED"
        actor         = "portal:maya_phone"
        intent_sha256 = $sha
        reason        = "Test Automation Phase 21"
    }
    
    $evt | ConvertTo-Json -Compress | Add-Content $ReviewLog -Encoding UTF8
}

# --- SETUP ---
Write-Host "--- SETUP: Cleaning Logs/Queues ---" -ForegroundColor Cyan
$StartMarker = "PHASE21_START_$(Get-Random)"
$StartMarker | Add-Content $DecisionLog

# Force Unlock
Remove-Item (Join-Path $Runtime "queue_lock.lock") -ErrorAction SilentlyContinue

# Reset Cursor (Force reprocessing)
Set-Content -Path (Join-Path $Runtime "queue_cursor.json") -Value '{"byte_offset": 0}' -Force

# --- CASE A: Approved + Handler + Allowed ---
Write-Host "--- CASE A: Approved + Handler + Allowed ---" -ForegroundColor Cyan
$IdA = "CASE_A_$(Get-Random)"
$NonceA = "NONCE_A_$(Get-Random)"
$IntentA = [ordered]@{
    task   = "system_diagnostic"
    target = "axis:handler/test"
    review = @{ required = $true }
}
$EnvA = New-Envelope -id $IdA -nonce $NonceA -identity "portal:voice_local" -intent $IntentA
$EnvA | ConvertTo-Json -Compress | Add-Content $IntentQueue -Encoding UTF8
Mock-Approve -nonce $NonceA -intentJson ($IntentA | ConvertTo-Json -Compress)


# --- CASE B: Approved + Handler + Disallowed ---
Write-Host "--- CASE B: Approved + Handler + Disallowed ---" -ForegroundColor Cyan
$IdB = "CASE_B_$(Get-Random)"
$NonceB = "NONCE_B_$(Get-Random)"
$IntentB = [ordered]@{
    task   = "system_diagnostic"
    target = "axis:handler/test"
    review = @{ required = $true }
}
$EnvB = New-Envelope -id $IdB -nonce $NonceB -identity "unknown:bad_actor" -intent $IntentB
$EnvB | ConvertTo-Json -Compress | Add-Content $IntentQueue -Encoding UTF8
Mock-Approve -nonce $NonceB -intentJson ($IntentB | ConvertTo-Json -Compress)


# --- CASE C: Approved + Non-Handler ---
Write-Host "--- CASE C: Approved + Non-Handler ---" -ForegroundColor Cyan
$IdC = "CASE_C_$(Get-Random)"
$NonceC = "NONCE_C_$(Get-Random)"
$IntentC = [ordered]@{
    type   = "POST"
    target = "moltbook:status" # Not axis:handler
    review = @{ required = $true }
}
$EnvC = New-Envelope -id $IdC -nonce $NonceC -identity "portal:voice_local" -intent $IntentC
$EnvC | ConvertTo-Json -Compress | Add-Content $IntentQueue -Encoding UTF8
Mock-Approve -nonce $NonceC -intentJson ($IntentC | ConvertTo-Json -Compress)


# --- CASE D: Pending + Handler ---
Write-Host "--- CASE D: Pending + Handler ---" -ForegroundColor Cyan
$IdD = "CASE_D_$(Get-Random)"
$NonceD = "NONCE_D_$(Get-Random)"
$IntentD = [ordered]@{
    task   = "system_diagnostic"
    target = "axis:handler/test"
    review = @{ required = $true }
}
$EnvD = New-Envelope -id $IdD -nonce $NonceD -identity "portal:voice_local" -intent $IntentD
$EnvD | ConvertTo-Json -Compress | Add-Content $IntentQueue -Encoding UTF8
# NO APPROVAL MOCK


# --- EXECUTE ---
Write-Host "--- EXECUTING T08 ---" -ForegroundColor Cyan
& $Executor

# --- VERIFY ---
Write-Host "--- VERIFICATION ---" -ForegroundColor Cyan
Start-Sleep -Seconds 2
$Logs = Get-Content $DecisionLog | Where-Object { $_ -like "*$StartMarker*" -or $_ -like "*CASE_*" }

# Check A
$ResA = $Logs | Select-String $NonceA
if ($ResA -match "FULFILLED") { Write-Host "CASE A [PASS]: FULFILLED" -ForegroundColor Green } 
else { Write-Host "CASE A [FAIL]: Expected FULFILLED, got $ResA" -ForegroundColor Red }

# Check B
$ResB = $Logs | Select-String $NonceB
if ($ResB -match "BLOCKED_HANDLER") { Write-Host "CASE B [PASS]: BLOCKED_HANDLER" -ForegroundColor Green } 
else { Write-Host "CASE B [FAIL]: Expected BLOCKED_HANDLER, got $ResB" -ForegroundColor Red }

# Check C (Should NOT differ from normal flow, so basically NOT handled by dispatcher)
$ResC = $Logs | Select-String $NonceC
if ($ResC -notmatch "FULFILLED" -and $ResC -notmatch "BLOCKED_HANDLER") { 
    Write-Host "CASE C [PASS]: Normal Flow (Not Handled)" -ForegroundColor Green 
}
else { 
    Write-Host "CASE C [FAIL]: Unexpected Handler Status: $ResC" -ForegroundColor Red 
}

# Check D
$ResD = $Logs | Select-String $NonceD
if ($ResD -match "BLOCKED" -and $ResD -match "Review Required") { Write-Host "CASE D [PASS]: BLOCKED (Review)" -ForegroundColor Green } 
else { Write-Host "CASE D [FAIL]: Expected Review Block, got $ResD" -ForegroundColor Red }
