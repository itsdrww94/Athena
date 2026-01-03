# Athena CLI Toolchain Setup
# Installs modern command-line utilities for a "Super User" experience on Windows.

Write-Host "Initializing Athena CLI Toolchain Upgrade..." -ForegroundColor Cyan

# --- 1. Winget Installations ---
Write-Host "`nInstalling WinGet Packages..." -ForegroundColor Magenta

$winget_tools = @(
    "Starship.Starship",
    "ajeetdsouza.zoxide",
    "junegunn.fzf",
    "sharkdp.fd",
    "BurntSushi.ripgrep.MSVC",
    "sharkdp.bat",
    "eza-community.eza",
    "dbrgn.tealdeer"
)

foreach ($tool in $winget_tools) {
    Write-Host "   Installing $tool..." -NoNewline
    winget install -e --id $tool --accept-source-agreements --accept-package-agreements | Out-Null
    if ($?) { Write-Host " Done" -ForegroundColor Green } else { Write-Host " Check (Might be installed)" -ForegroundColor Yellow }
}

# --- 2. Pipx Installations ---
Write-Host "`nInstalling Python CLIs via pipx..." -ForegroundColor Magenta

# Ensure pipx is installed
if (-not (Get-Command pipx -ErrorAction SilentlyContinue)) {
    Write-Host "   Installing pipx..."
    py -3.14 -m pip install --user pipx
    py -3.14 -m pipx ensurepath
}

$pipx_tools = @(
    "httpie",
    "glances",
    "pgcli",
    "litecli",
    "virtualenv"
)

foreach ($tool in $pipx_tools) {
    Write-Host "   Installing $tool..." -NoNewline
    pipx install $tool | Out-Null
    if ($?) { Write-Host " Done" -ForegroundColor Green } else { Write-Host " Check (Might be installed)" -ForegroundColor Yellow }
}

# --- 3. NPM Installations ---
Write-Host "`nInstalling Node CLIs..." -ForegroundColor Magenta

if (Get-Command npm -ErrorAction SilentlyContinue) {
    Write-Host "   Installing diff-so-fancy..." -NoNewline
    npm install -g diff-so-fancy | Out-Null
    if ($?) { Write-Host " Done" -ForegroundColor Green } else { Write-Host " Check" -ForegroundColor Yellow }
} else {
    Write-Host "   npm not found. Skipping Node tools." -ForegroundColor Yellow
}

Write-Host "`nToolchain Upgrade Complete!" -ForegroundColor Green
Write-Host "You may need to restart your terminal for all tools to be available." -ForegroundColor Cyan
