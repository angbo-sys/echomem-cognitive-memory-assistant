@echo off
setlocal

cd /d "%~dp0\.."

echo ========================================
echo EchoMem Windows EXE Builder
echo ========================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] python was not found in PATH.
    echo Please run this script from Anaconda Prompt inside the EchoMem environment.
    pause
    exit /b 1
)

python scripts\secret_scan.py --strict
if errorlevel 1 (
    echo.
    echo [ERROR] Secret scan failed. Stop building.
    pause
    exit /b 1
)

python -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
    echo PyInstaller is not installed. Installing it into the current Python environment...
    python -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller.
        pause
        exit /b 1
    )
)

python scripts\prepare_windows_payload.py
if errorlevel 1 (
    echo [ERROR] Failed to prepare Windows payload.
    pause
    exit /b 1
)

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --name EchoMem ^
    --console ^
    --add-data ".build\windows_payload\payload;payload" ^
    --collect-all streamlit ^
    --hidden-import pandas ^
    --hidden-import chromadb ^
    --hidden-import mem0 ^
    --hidden-import llama_cloud ^
    --hidden-import llama_index.core ^
    --hidden-import cognee ^
    packaging\windows_launcher.py

if errorlevel 1 (
    echo.
    echo [ERROR] PyInstaller build failed.
    pause
    exit /b 1
)

if exist ".env" (
    echo.
    echo [INFO] .env was found in the project root.
    if "%ECHOMEM_COPY_ENV%"=="1" (
        copy ".env" "dist\EchoMem\.env" >nul
        echo [WARN] Copied .env to dist\EchoMem\.env for local personal use.
        echo [WARN] Do not upload or share this dist folder.
    ) else (
        echo [INFO] For security, it was NOT embedded into the exe or copied to dist.
        echo [INFO] If this is only for your own computer, run:
        echo [INFO] set ECHOMEM_COPY_ENV=1
        echo [INFO] scripts\build_windows_exe.bat
    )
)

echo.
echo Build finished:
echo dist\EchoMem\EchoMem.exe
echo.
echo Double-click EchoMem.exe to start the UI.
echo Keep .env next to EchoMem.exe when real API keys are needed.
echo.
pause
exit /b 0
