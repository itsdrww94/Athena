<#
.SYNOPSIS
Runs a Python script with the project root added to PYTHONPATH.
Fixes "ModuleNotFoundError" when running agents from the root directory.

.EXAMPLE
.\run_agent.ps1 agents/parlay/agent.py --command /bag_watch
#>

param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$ScriptPath,

    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$ScriptArgs
)

# Get Project Root (Directory where this script lives)
$ProjectRoot = $PSScriptRoot

# Add to PYTHONPATH
$env:PYTHONPATH = "$ProjectRoot;$env:PYTHONPATH"

# Print Debug Info
Write-Host "[ATHENA RUNNER]" -ForegroundColor Cyan
Write-Host " Context: $ProjectRoot" -ForegroundColor DarkGray
Write-Host " Script:  $ScriptPath" -ForegroundColor DarkGray
Write-Host "--------------------------------" -ForegroundColor DarkGray

# Run Python
if ($ScriptArgs) {
    python $ScriptPath $ScriptArgs
} else {
    python $ScriptPath
}
