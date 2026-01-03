# Athena Global Fixer (ASCII Only)
# Run this to force Athena to point to the new version (Athena_Project)

Write-Host "Diagnosing 'athena' command..." -ForegroundColor Cyan
Get-Command athena -ErrorAction SilentlyContinue | Format-List Name, CommandType, Definition

Write-Host "`nRemoving old aliases..." -ForegroundColor Magenta
Remove-Item Alias:athena -ErrorAction SilentlyContinue -Force
Remove-Item Function:athena -ErrorAction SilentlyContinue -Force
del function:athena -ErrorAction SilentlyContinue

Write-Host "Setting new global command..." -ForegroundColor Cyan
$FunctionDef = 'function athena { Set-Location "c:\Users\itsdr\OneDrive\project Athena\Athena_Project"; .\athena.bat $args }'

# 1. Set in current session immediately
Invoke-Expression $FunctionDef

# 2. Persist to Profile
$ProfilePath = $PROFILE
if ([string]::IsNullOrEmpty($ProfilePath)) {
    $ProfilePath = Join-Path $Home 'Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1'
}
if (!(Test-Path (Split-Path $ProfilePath))) { New-Item -ItemType Directory -Path (Split-Path $ProfilePath) -Force }
if (!(Test-Path $ProfilePath)) { New-Item -ItemType File -Path $ProfilePath -Force }
Add-Content -Path $ProfilePath -Value "`n$FunctionDef"

Write-Host "FIXED! The 'athena' command has been updated." -ForegroundColor Green
Write-Host "Target: c:\Users\itsdr\OneDrive\project Athena\Athena_Project" -ForegroundColor Gray
Write-Host "Launch new Athena now..." -ForegroundColor Green
Start-Sleep -Seconds 2
athena
