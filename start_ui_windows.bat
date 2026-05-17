@echo off
setlocal

cd /d "%~dp0"

if "%ECHOMEM_ENV%"=="" set "ECHOMEM_ENV=echomem-test"
if "%ECHOMEM_PORT%"=="" set "ECHOMEM_PORT=8501"

echo ========================================
echo EchoMem Windows UI Launcher
echo ========================================
echo Project: %CD%
echo Conda env: %ECHOMEM_ENV%
echo Port: %ECHOMEM_PORT%
echo.

if not exist ".env" (
    echo [WARN] .env was not found.
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo Created .env from .env.example.
        echo Please edit .env and fill in your API keys, then run this script again.
    ) else (
        echo .env.example was not found. Please create .env manually.
    )
    echo.
    pause
    exit /b 1
)

where conda >nul 2>nul
if errorlevel 1 (
    echo [ERROR] conda was not found in PATH.
    echo Please open Anaconda Prompt, cd to this project folder, then run:
    echo start_ui_windows.bat
    echo.
    pause
    exit /b 1
)

echo Starting EchoMem UI...
echo URL: http://localhost:%ECHOMEM_PORT%
echo Press Ctrl+C in this window to stop the server.
echo.

conda run -n "%ECHOMEM_ENV%" streamlit run ui/app.py --server.port %ECHOMEM_PORT% --server.headless false

set "EXIT_CODE=%ERRORLEVEL%"
echo.
if not "%EXIT_CODE%"=="0" (
    echo [ERROR] EchoMem UI exited with code %EXIT_CODE%.
    echo Please check that the Conda environment exists and Streamlit is installed.
) else (
    echo EchoMem UI stopped.
)
echo.
pause
exit /b %EXIT_CODE%
