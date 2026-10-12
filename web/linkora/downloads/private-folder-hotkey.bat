@echo off
cls
setlocal
title WinForge - Private Folder Hotkey Setup
color 0A
echo ============================================================
echo   WINFORGE - PRIVATE FOLDER HOTKEY SETUP
echo ============================================================
echo.
echo This creates a hidden folder in your Documents folder and
echo a Start Menu shortcut to open it with CTRL + ALT + P.
echo.
echo IMPORTANT: Hidden folders are NOT password-protected.
echo Anyone who knows where to look can reveal them. This script
echo does not move, copy, encrypt, or delete your existing files.
echo.
choice /C YN /N /M "Continue with setup? (Y/N): "
if errorlevel 2 goto :cancel
echo.
echo [1/3] Preparing private folder and keyboard shortcut...
set "WF_PS=%TEMP%\WinForgePrivateFolderSetup.ps1"
>"%WF_PS%" echo $ErrorActionPreference = 'Stop'
>>"%WF_PS%" echo $folder = Join-Path $env:USERPROFILE 'Documents\Personal Files'
>>"%WF_PS%" echo $shortcutDir = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs\Windows Tools'
>>"%WF_PS%" echo $shortcutPath = Join-Path $shortcutDir 'Personal Folder Access.lnk'
>>"%WF_PS%" echo New-Item -ItemType Directory -Path $folder -Force ^| Out-Null
>>"%WF_PS%" echo New-Item -ItemType Directory -Path $shortcutDir -Force ^| Out-Null
>>"%WF_PS%" echo $item = Get-Item -LiteralPath $folder -Force
>>"%WF_PS%" echo $item.Attributes = $item.Attributes -bor [IO.FileAttributes]::Hidden -bor [IO.FileAttributes]::System
>>"%WF_PS%" echo $shell = New-Object -ComObject WScript.Shell
>>"%WF_PS%" echo $link = $shell.CreateShortcut($shortcutPath)
>>"%WF_PS%" echo $link.TargetPath = Join-Path $env:WINDIR 'explorer.exe'
>>"%WF_PS%" echo $link.Arguments = '"' + $folder + '"'
>>"%WF_PS%" echo $link.WorkingDirectory = $folder
>>"%WF_PS%" echo $link.Hotkey = 'CTRL+ALT+P'
>>"%WF_PS%" echo $link.Description = 'Open your personal files folder'
>>"%WF_PS%" echo $link.Save()
>>"%WF_PS%" echo Write-Output ('FOLDER=' + $folder)
>>"%WF_PS%" echo Write-Output ('SHORTCUT=' + $shortcutPath)
>>"%WF_PS%" echo Start-Process explorer.exe -ArgumentList ('"' + $folder + '"')
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%WF_PS%"
set "WF_RESULT=%ERRORLEVEL%"
del /q "%WF_PS%" >nul 2>&1
if not "%WF_RESULT%"=="0" goto :failed
echo.
echo [2/3] Setup completed.
echo [3/3] Press CTRL + ALT + P to open your Personal Files folder.
echo.
echo Folder: %%USERPROFILE%%\Documents\Personal Files
echo Shortcut: Start Menu ^> Windows Tools ^> Personal Folder Access
echo.
echo SECURITY NOTE: This is visual hiding only, not encryption.
echo Use Windows Device Encryption or a reputable encrypted vault
echo for genuinely sensitive files. Keep a separate backup.
echo.
pause
exit /b 0
:cancel
echo.
echo Setup cancelled. No changes were made.
pause
exit /b 0
:failed
echo.
echo ERROR: Setup could not finish. Check that PowerShell and Windows Script Host are available.
echo No existing personal files were moved or deleted.
pause
exit /b 1
