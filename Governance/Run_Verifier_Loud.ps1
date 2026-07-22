$ErrorActionPreference = "Continue"
$log = Join-Path "D:\Infinite\Infinity\Governance" "verifier_loud.log"
"--- START VERIFIER ---" | Out-File $log
& "D:\Infinite\Infinity\Governance\Axis_Verify_Replay.ps1" | Out-File $log -Append
"--- END VERIFIER ---" | Out-File $log -Append
