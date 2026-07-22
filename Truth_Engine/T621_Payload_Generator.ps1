<#
.SYNOPSIS
  T621_Payload_Generator.ps1
  Generates signed "Forensic Proof" intents for the 217th Cycle.
#>

$RectificationPath = "D:\Infinite\Infinity\Narrative\Rectification_Map.jsonl"
$IntentQueue = "D:\Infinite\Infinity\Runtime\Decision\intent_queue.jsonl"
$IdentityFile = "D:\Infinite\Infinity\Runtime\Identity\identity_registry.json"

Write-Host "[FORENSIC] Generating Actuation Payloads..." -ForegroundColor Red

# 1. Identity Check
$reg = Get-Content $IdentityFile | ConvertFrom-Json
$id = $reg.identities."portal:maya_phone"
$secret = $id.shared_secret

function Compute-Signature {
    param($message)
    $hmac = [System.Security.Cryptography.HMACSHA256]::new([Text.Encoding]::UTF8.GetBytes($secret))
    $hash = $hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($message))
    return [BitConverter]::ToString($hash).Replace("-", "").ToLower()
}

# 2. Process Rectification Nodes
$nodes = Get-Content $RectificationPath | ConvertFrom-Json
foreach ($node in $nodes) {
    Write-Host "[FORENSIC] Generating proof for: $($node.payload.title)" -ForegroundColor Yellow
    
    $intent = @{
        schema = "axis.intent.v1"
        kind   = "ACTUATE_RECTIFICATION"
        payload = @{
            id      = "PROOF-" + $node.payload.id
            node_id = $node.payload.id
            title   = $node.payload.title
            target  = $node.payload.target
            weight  = $node.payload.weight
        }
    }
    
    $json = $intent | ConvertTo-Json -Compress
    $sig = Compute-Signature -message $json
    
    $bundle = @{
        intent = $intent
        signature = $sig
        identity = "portal:maya_phone"
    }
    
    $bundle | ConvertTo-Json -Compress | Add-Content $IntentQueue
}

Write-Host "[FORENSIC] Proofs enqueued. Almighty Engine will actuate." -ForegroundColor Green
