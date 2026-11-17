@echo off
setlocal
cd /d "%~dp0"
echo Installing project dependencies...
py -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Dependency installation failed. Check internet and Python installation.
  pause
  exit /b 1
)
echo.
echo Running safe local database API tests using temporary SQLite...
py test_database.py
if errorlevel 1 (
  echo.
  echo Some tests failed. Copy the full output when asking for help.
) else (
  echo.
  echo All local API tests passed.
)
pause
