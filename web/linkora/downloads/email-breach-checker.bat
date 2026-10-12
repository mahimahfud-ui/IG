@echo off
cls
setlocal EnableExtensions
title WinForge - Check Email Breach Exposure

echo ============================================================
echo   WinForge - Personal Email Breach Check
echo ============================================================
echo.
echo This opens the official Have I Been Pwned website.
echo It does NOT ask for or collect your email password.
echo Never enter your Gmail password on a breach-check website.
echo.

start "" "https://haveibeenpwned.com/"
if errorlevel 1 (
  echo [ERROR] Could not open the browser automatically.
  echo Open this address manually: https://haveibeenpwned.com/
  echo.
  pause
  exit /b 1
)

echo.
echo [1/2] Enter your own email address on the official website.
echo [2/2] Review the breach results and follow its guidance.
echo.
echo IMPORTANT:
echo - A breach result does not prove anyone logged into your account.
echo - This website does not reveal your full Gmail login history.
echo - To check Google account sign-ins, visit:
echo   https://myaccount.google.com/security
echo - If exposed, change reused passwords and enable 2-Step Verification.
echo.
pause
endlocal
