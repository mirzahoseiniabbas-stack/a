@echo off
cd /d "%~dp0"
title Heyat

echo.
echo Please wait. The first time can take a few minutes.
echo Do not close this window.
echo.

set "RUN="
where py >nul 2>&1 && set "RUN=py -3"
if not defined RUN (
  where python >nul 2>&1 && set "RUN=python"
)

if not defined RUN (
  echo Python 3.12 is not installed.
  echo The Microsoft Store will open. Install Python 3.12, then double-click start.bat again.
  start ms-windows-store://search/?query=Python%%203.12
  echo.
  pause
  exit /b 1
)

call %RUN% -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
  echo.
  echo The first download failed. Trying another source...
  call %RUN% -m pip install -r "%~dp0requirements.txt" -i https://mirror.arvancloud.ir/pypi/simple --trusted-host mirror.arvancloud.ir
)

if errorlevel 1 (
  echo.
  echo Install failed. Take a photo of this window and send it.
  pause
  exit /b 1
)

echo.
echo Opening the page. Keep this window open.
start "" cmd /c "timeout /t 4 /nobreak >nul & start http://127.0.0.1:8080/"
call %RUN% -m heyat
echo.
echo The program stopped.
pause
