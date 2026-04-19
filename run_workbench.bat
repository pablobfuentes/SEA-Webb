@echo off
REM Thin wrapper: repo root = this file's directory. Delegates to scripts\run_workbench.ps1
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\run_workbench.ps1" %*
exit /b %ERRORLEVEL%
