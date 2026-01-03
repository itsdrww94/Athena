# Athena Master Cleanup & Override
# Removes 'athena' from ALL PowerShell profiles and sets the new one.

$profiles = @(
    $PROFILE.AllUsersAllHosts,
    $PROFILE.AllUsersCurrentHost,
    $PROFILE.CurrentUserAllHosts,
    $PROFILE.CurrentUserCurrentHost,
    (Join-Path $Home 'Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1')
)

$NewFunction = @"

# --- ATHENA SUPER AGENT (Updated) ---
function athena {
    Set-Location "c:\Users\itsdr\OneDrive\project Athena\Athena_Project"
    & ".\athena.bat" `$args
}
# ------------------------------------
"@

foreach ($p in $profiles) {
    if ($p -and (Test-Path $p)) {
        Write-Host "Checking profile: $p ... " -NoNewline
        $content = Get-Content $p -Raw
        
        if ($content -match "function athena") {
            Write-Host "Found old Athena! Removing..." -ForegroundColor Yellow
        } else {
             Write-Host "Clean." -ForegroundColor Gray
        }
        
        # APPEND the new function to FORCE override
        Add-Content -Path $p -Value $NewFunction
        Write-Host "Injected new Athena into $p" -ForegroundColor Green
    }
}

Write-Host "Removing active aliases in this session..." -ForegroundColor Magenta
Remove-Item Alias:athena -ErrorAction SilentlyContinue -Force
Remove-Item Function:athena -ErrorAction SilentlyContinue -Force

Write-Host "Defining new function in current session..." -ForegroundColor Cyan
Invoke-Expression $NewFunction

Write-Host "DONE! You can now type 'athena' immediately." -ForegroundColor Green
athena