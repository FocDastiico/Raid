$ErrorActionPreference = "Continue"

Write-Host "Limpando cache DNS..." -ForegroundColor Cyan
ipconfig /flushdns

Write-Host "Resetando Winsock..." -ForegroundColor Cyan
netsh winsock reset

Write-Host "Resetando pilha TCP/IP..." -ForegroundColor Cyan
netsh int ip reset

Write-Host "Configurando DNS IPv4 publico..." -ForegroundColor Cyan
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -AddressFamily IPv4 -ServerAddresses ("8.8.8.8", "1.1.1.1")

Write-Host "Configurando DNS IPv6 publico..." -ForegroundColor Cyan
Set-DnsClientServerAddress -InterfaceAlias "Ethernet" -AddressFamily IPv6 -ServerAddresses ("2001:4860:4860::8888", "2606:4700:4700::1111")

Write-Host "Mostrando DNS aplicado..." -ForegroundColor Green
Get-DnsClientServerAddress -InterfaceAlias "Ethernet" | Format-Table -AutoSize

Write-Host ""
Write-Host "Concluido. Reinicie o PC para finalizar o reset de rede." -ForegroundColor Yellow
