Import-Module D:\Infinite\Infinity\Truth_Engine\T09_KeyRing.psm1 -Force

$VaultPath = "D:\Infinite\Infinity\Secrets\keyring.json"
if (-not (Test-Path $VaultPath)) { Write-Error "Vault not found"; exit 1 }

$vault = Get-Content $VaultPath -Raw | ConvertFrom-Json

# Calculate hash of the keys
$json = $vault.keys | ConvertTo-Json -Compress
$sha = [System.Security.Cryptography.SHA256]::Create()
$bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
$hashBytes = $sha.ComputeHash($bytes)
$hash = ($hashBytes | ForEach-Object { $_.ToString("x2") }) -join ""

if (-not $vault.vault_meta) {
    $vault | Add-Member -MemberType NoteProperty -Name "vault_meta" -Value @{ created_ts = (Get-Date).ToString("o"); last_modified_ts = (Get-Date).ToString("o"); container_hash = "" }
}

$vault.vault_meta.container_hash = $hash
$vault.vault_meta.last_modified_ts = (Get-Date).ToString("o")

$vault | ConvertTo-Json -Depth 10 | Set-Content $VaultPath -Encoding UTF8 -Force
Write-Host "Vault re-sealed with hash: $hash" -ForegroundColor Green
