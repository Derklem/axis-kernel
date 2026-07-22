<#
.SYNOPSIS
  Voice STT Stub (Manual Injection)
.DESCRIPTION
  Simulates an STT engine by accepting text input and writing it to voice_inbox.jsonl.
  Use this to test the Voice Bridge without a microphone.
#>

[CmdletBinding()]
param(
    [string]$Root = "D:\Infinite\Infinity"
)

$VoiceDir = Join-Path $Root "Runtime\Decision\Voice"
$InboxPath = Join-Path $VoiceDir "voice_inbox.jsonl"

function New-GuidStr { [guid]::NewGuid().ToString() }

Write-Host "Voice STT Simulator - Type 'exit' to quit." -ForegroundColor Cyan

while ($true) {
    $text = Read-Host "Microphone Input"
    if ($text -eq "exit") { break }
    if ([string]::IsNullOrWhiteSpace($text)) { continue }
    
    $utt = [ordered]@{
        schema = "axis.voice.utterance.v1"
        ts_utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.000Z")
        utterance_id = ("VOICE-" + (New-GuidStr).Substring(0,8))
        text = $text
        confidence = 0.99
        source = @{ device="pc"; mic="manual_stub" }
    }
    
    $json = $utt | ConvertTo-Json -Compress
    [System.IO.File]::AppendAllText($InboxPath, $json + "`n", [System.Text.Encoding]::UTF8)
    Write-Host "Captured: $text" -ForegroundColor Green
    
    # Optional: Trigger bridge immediately
    # & "$VoiceDir\Voice_IntentBridge.ps1"
}
