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

set "PAYLOAD_FLAGS="
if "%ECHOMEM_EMBED_ENV%"=="1" (
    set "PAYLOAD_FLAGS=--include-env"
    echo [WARN] ECHOMEM_EMBED_ENV=1 is enabled.
    echo [WARN] The .env file will be embedded into EchoMem.exe for private local testing.
    echo [WARN] Do not upload, share, or commit the generated exe.
    echo.
) else (
    python scripts\secret_scan.py --strict
    if errorlevel 1 (
        echo.
        echo [ERROR] Secret scan failed. Stop building.
        echo [INFO] If this is a private local build that intentionally embeds .env, run:
        echo [INFO] PowerShell: $env:ECHOMEM_EMBED_ENV = "1"
        echo [INFO] CMD: set ECHOMEM_EMBED_ENV=1
        pause
        exit /b 1
    )
)

if exist "requirements-windows.txt" (
    echo Installing Windows build/runtime dependencies...
    python -m pip install -r requirements-windows.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies from requirements-windows.txt.
        pause
        exit /b 1
    )
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

python scripts\prepare_windows_payload.py %PAYLOAD_FLAGS%
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
    if "%ECHOMEM_EMBED_ENV%"=="1" (
        echo [WARN] .env was embedded into EchoMem.exe for this private test build.
        echo [WARN] Do not upload or share dist\EchoMem\EchoMem.exe.
    ) else if "%ECHOMEM_COPY_ENV%"=="1" (
        copy ".env" "dist\EchoMem\.env" >nul
        echo [WARN] Copied .env to dist\EchoMem\.env for local personal use.
        echo [WARN] Do not upload or share this dist folder.
    ) else (
        echo [INFO] For security, it was NOT embedded into the exe or copied to dist.
        echo [INFO] If this is only for your own computer, run:
        echo [INFO] set ECHOMEM_EMBED_ENV=1
        echo [INFO] scripts\build_windows_exe.bat
        echo [INFO] Or keep the exe clean and copy .env next to it:
        echo [INFO] set ECHOMEM_COPY_ENV=1
        echo [INFO] scripts\build_windows_exe.bat
    )
)

echo.
echo Build finished:
echo dist\EchoMem\EchoMem.exe
echo.
echo Double-click EchoMem.exe to start the UI.
if "%ECHOMEM_EMBED_ENV%"=="1" (
    echo This private build has .env embedded in the exe payload.
) else (
    echo Keep .env next to EchoMem.exe when real API keys are needed.
)
echo.
pause
exit /b 0
