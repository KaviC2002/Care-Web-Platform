@echo off
cd "%~dp0"

echo Checking for Python installation...
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
  echo Python is not installed or not in your PATH. Please install Python and ensure it is added to your PATH.
  pause
  exit /b 1
)

if not exist "env" (
  echo Creating virtual environment...
  python -m venv env
  if %ERRORLEVEL% NEQ 0 (
    echo Failed to create virtual environment. Exiting.
    pause
    exit /b 1
  )
)

echo Activating virtual environment...
call env\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
  echo Activation script not found. Exiting.
  pause
  exit /b 1
)

echo Installing requirements...
pip install -r windows_requirements.txt
if %ERRORLEVEL% NEQ 0 (
  echo Failed to install requirements. Exiting.
  pause
  exit /b 1
)

echo Running app...
python main.py
if %ERRORLEVEL% NEQ 0 (
  echo Application encountered an error. Exiting.
  pause
  exit /b 1
)

echo Deactivating virtual environment...
deactivate
pause
