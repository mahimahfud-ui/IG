@echo off
cls
setlocal EnableExtensions
title WinForge - Update Installed Apps

echo ============================================================
echo   WinForge - Update Installed Windows Apps
echo ============================================================
echo.
echo This tool checks apps managed by Windows Package Manager
echo (winget), shows available updates, then asks before updating.
echo It does not update Windows itself or every app on your PC.
echo.

where winget >nul 2>&1
if errorlevel 1 (
  echo [ERROR] winget was not found.
  echo Install or update "App Installer" from Microsoft Store,
  echo then reopen this script.
  echo.
  pause
  exit /b 1
)

echo [1/3] Refreshing winget package sources...
winget source update
if errorlevel 1 (
  echo.
  echo [WARNING] Source refresh reported a problem. Continuing to check.
)

echo.
echo [2/3] Checking installed apps for available updates...
echo Review the list below. Some apps may not be managed by winget.
echo.
winget upgrade
if errorlevel 1 (
  echo.
  echo [WARNING] The update check returned a non-zero exit code.
  echo Check the messages above, your internet connection, and winget sources.
  echo.
)

echo.
choice /C YN /N /M "Install all available winget updates now? [Y/N]: "
if errorlevel 2 goto :CANCEL
if errorlevel 1 goto :UPDATE

:UPDATE
echo.
echo [3/3] Installing available updates...
echo Keep this window open. Some installers may ask for permission.
echo.
winget upgrade --all --accept-source-agreements --accept-package-agreements
set "UPDATE_RESULT=%ERRORLEVEL%"
echo.
if "%UPDATE_RESULT%"=="0" (
  echo [SUCCESS] winget finished the update command.
) else (
  echo [WARNING] winget returned exit code %UPDATE_RESULT%.
  echo Some packages may have failed, been skipped, or need manual action.
)
echo.
echo Tip: Run this again later to check for newly available updates.
pause
endlocal
exit /b %UPDATE_RESULT%

:CANCEL
echo.
echo [CANCELLED] No app updates were started.
pause
endlocal
exit /b 0
