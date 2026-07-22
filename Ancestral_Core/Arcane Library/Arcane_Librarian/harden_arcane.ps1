# Harden Arcane Library - Defender Script
Write-Host "🛡️ Hardening Arcane Library Access Points..." -ForegroundColor Red
Set-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows\DataCollection" -Name "AllowTelemetry" -Value 0
netsh advfirewall firewall add rule name="Block SSDP Discovery" dir=out action=block protocol=UDP localport=1900
Write-Host "✅ Arcane Library Hardened"
