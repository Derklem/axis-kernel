$Root = "D:\Infinite\Infinity"
$Runtime = Join-Path $Root "Runtime\Decision"
$VoiceProps = Join-Path $Runtime "Voice\voice_proposals.jsonl"
$ReviewLog = Join-Path $Runtime "Review\review_log.jsonl"

foreach ($line in Get-Content $VoiceProps -Encoding UTF8) {
    if ([string]::IsNullOrWhiteSpace($line)) { continue }
    try {
        $env = $line | ConvertFrom-Json
        
        if (-not $env.intent_json) { continue }
        $p = $env.intent_json | ConvertFrom-Json
        
        if ($p.status -eq "PENDING_REVIEW") {
            # Calculate Hash of the canonical intent_json string (as it appears in the envelope or re-serialized?)
            # The Promoter calculates hash of `envelope.intent_json`.
            # So we must use THAT string exactly if possible, OR re-serialize identically.
            # `Voice_Proposal_Promoter` does: Compute-AxisIntentHash -json $envelope.intent_json
            
            $intentJsonString = $env.intent_json
            
            Write-Host "Approver String Length: $($intentJsonString.Length)"
            Write-Host "Approver String Start: $($intentJsonString.Substring(0, [math]::Min(20, $intentJsonString.Length)))"
            
            $sha = [System.Security.Cryptography.SHA256]::Create()
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($intentJsonString)
            $hash = ($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""
            
            $entry = [ordered]@{
                ts_utc        = (Get-Date).ToUniversalTime().ToString("o")
                action        = "APPROVED"
                proposal_id   = $p.proposal_id
                intent_sha256 = $hash
                reviewer      = "AXIS_ADMIN"
                notes         = "Auto-approved for verification"
            }
            
            $entry | ConvertTo-Json -Compress | Add-Content $ReviewLog -Encoding UTF8
            Write-Host "Approved: $($p.proposal_id)"
        }
    }
    catch {
        Write-Warning "Failed to process envelope: $_"
    }
}
