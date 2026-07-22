# Sync-AxisCapsule.ps1
$CapsulePath = "D:\Infinite\Infinity\Governance\Sovereign_State_Capsule.json"
$capsule = Get-Content $CapsulePath -Raw | ConvertFrom-Json

$executor = "D:\Infinite\Infinity\Runtime\Decision\T08_Executor.ps1"
$constraints = "D:\Infinite\Infinity\Governance\Constitutional_Constraints.json"
$run_t08 = "D:\Infinite\Infinity\Runtime\Decision\Run_T08.ps1"

$eHash = "sha256:" + (Get-FileHash $executor).Hash
$cHash = "sha256:" + (Get-FileHash $constraints).Hash
$rHash = "sha256:" + (Get-FileHash $run_t08).Hash

$capsule.verification.authority_hashes.executor_sha256 = $eHash
$capsule.verification.authority_hashes.constraints_sha256 = $cHash
$capsule.verification.authority_hashes.run_t08_sha256 = $rHash

$capsule | ConvertTo-Json -Depth 20 | Set-Content $CapsulePath -Encoding UTF8
Write-Host "Capsule Synced."
Write-Host "Executor: $eHash"
Write-Host "Constraints: $cHash"
Write-Host "Run_T08: $rHash"
