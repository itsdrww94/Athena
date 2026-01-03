# Athena Global Setup Script
# Adds a global 'athena' command to your PowerShell profile

$ProfilePath = $PROFILE
$ProjectDir = "c:\Users\itsdr\OneDrive\project Athena\Athena_Project"
$BatFile = "$ProjectDir\athena.bat"

Write-Host "🚀 Setting up Athena Global Command..." -ForegroundColor Cyan

# Check if profile exists, create if not
if (-not (Test-Path $ProfilePath)) {
    New-Item -Path $ProfilePath -ItemType File -Force | Out-Null
    Write-Host "Created new PowerShell profile at $ProfilePath" -ForegroundColor Green
}

# FORCE REMOVAL of old aliases/functions to prevent conflicts
Write-Host "🧹 Cleaning up old Athena shortcuts..." -ForegroundColor Yellow
Remove-Item Alias:athena -ErrorAction SilentlyContinue -Force
Remove-Item Function:athena -ErrorAction SilentlyContinue -Force

# The PowerShell Function to add
$AthenaFunction = @"

# --- ATHENA SUPER AGENT ---
function athena {
    Set-Location "$ProjectDir"
    & ".\athena.bat" `$args
}
# --------------------------
"@

# Append to profile
Add-Content -Path $ProfilePath -Value $AthenaFunction

Write-Host "✅ Athena added to PowerShell Profile!" -ForegroundColor Green
Write-Host "🔄 Reloading profile..." -ForegroundColor Cyan

# Reload profile in current session
. $ProfilePath

Write-Host "🎉 Setup Complete! You can now type 'athena' from ANY folder." -ForegroundColor Magenta
Write-Host "Try it now: athena" -ForegroundColor White
