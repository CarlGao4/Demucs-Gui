where pwsh.exe >nul 2>&1 && set "PWSH=pwsh.exe" || set "PWSH=powershell.exe"
"%PWSH%" -NoProfile -ExecutionPolicy Bypass -Command "& '%~dp0debug.ps1' -StdErrFile '%~dpn1.log' %*"