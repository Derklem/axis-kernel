$walletPath = "C:\Halcyon\phantom_wallet"
$ledgerPath = "C:\Halcyon\lattice\luck_ledger.log"
$bindPath = "C:\Halcyon\lattice\shimmer_bind.json"

New-Item -ItemType Directory -Force -Path $walletPath | Out-Null
New-Item -ItemType Directory -Force -Path (Split-Path $ledgerPath) | Out-Null

$wallets = Get-ChildItem -Path $walletPath -Filter *.pwl -ErrorAction SilentlyContinue
$ledgerEntries = @()

foreach ($wallet in $wallets) {
    $id = [System.IO.Path]::GetFileNameWithoutExtension($wallet.Name)
    $value = [double](Get-Content $wallet.FullName -ErrorAction SilentlyContinue)
    $ledgerEntries += @{id=$id; shimmer=$value}
}

$ledgerJson = $ledgerEntries | ConvertTo-Json -Compress
Set-Content -Path $bindPath -Value $ledgerJson

$timestamp = Get-Date -Format s
$entry = "[$timestamp] :: Memory sync complete -- $($wallets.Count) wallets indexed"
Add-Content -Path $ledgerPath -Value $entry

Write-Host "Synced $($wallets.Count) phantom wallets --> shimmer ledger updated."
