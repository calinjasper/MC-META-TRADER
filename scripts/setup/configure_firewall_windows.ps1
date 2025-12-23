# Configure Windows Firewall for PocketBase
# Run this script as Administrator on the server (192.168.173.112)

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  Configuring Windows Firewall for PocketBase" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[ERROR] This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "[INFO] Adding firewall rule for PocketBase (port 8090)..." -ForegroundColor Yellow

# Remove existing rule if it exists
$existingRule = Get-NetFirewallRule -DisplayName "PocketBase" -ErrorAction SilentlyContinue
if ($existingRule) {
    Write-Host "[INFO] Removing existing PocketBase firewall rule..." -ForegroundColor Yellow
    Remove-NetFirewallRule -DisplayName "PocketBase"
}

# Add new firewall rule
try {
    New-NetFirewallRule -DisplayName "PocketBase" `
        -Description "Allow PocketBase database connections on port 8090" `
        -Direction Inbound `
        -LocalPort 8090 `
        -Protocol TCP `
        -Action Allow `
        -Profile Any
    
    Write-Host "[SUCCESS] Firewall rule added successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "PocketBase port 8090 is now open for incoming connections" -ForegroundColor Green
    Write-Host ""
} catch {
    Write-Host "[ERROR] Failed to add firewall rule: $_" -ForegroundColor Red
    exit 1
}

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Start PocketBase with: scripts\setup\start_pocketbase_network.bat" -ForegroundColor White
Write-Host "2. Test connection from client: python tools\test_pocketbase_connection.py" -ForegroundColor White
Write-Host ""

