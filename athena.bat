@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0
py -3.14 athena_cli.py %*

