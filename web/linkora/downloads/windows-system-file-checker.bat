@echo off
cls
setlocal EnableExtensions
title WinForge - Windows System File Repair

echo ============================================================
echo   WinForge - Windows System File Checker
echo ============================================================
echo.
echo This runs Microsoft's built-in SFC scan to check protected
echo Windows system files and repair problems when possible.
echo It does not replace a full Blue Screen diagnosis.
echo.

fltmc >nul 2>&1
if errorlevel 1 (
  echo [INFO] Administrator permission is required.
  echo A Windows permission prompt will appear.
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%ComSpec%' -ArgumentList '/c ""%~f0""' -Verb RunAs"
  if errorlevel 1 (
    echo [ERROR] Could not request Administrator permission.
    pause
    exit /b 1
  )
  exit /b
)

echo [1/2] Running SFC /scannow...
echo This may take several minutes. Do not close this window.
echo.
sfc /scannow
set "SFC_RESULT=%ERRORLEVEL%"

echo.
echo ============================================================
echo SCAN FINISHED
echo ============================================================
if "%SFC_RESULT%"=="0" (
  echo SFC completed. Read the scan message above to see whether
  echo Windows found and repaired corrupted files.
) else (
  echo SFC returned exit code %SFC_RESULT%.
  echo Read the message above. If repair failed, run DISM health
  echo repair commands or check the CBS log with technical help.
)
echo.
echo IMPORTANT:
echo - This scan is not guaranteed to fix every slow-PC or BSOD issue.
echo - Keep important files backed up, especially before major repairs.
echo - If Windows reports it could not repair some files, do not assume
echo   that the problem is fixed.
echo.
pause
endlocal
exit /b %SFC_RESULT%
