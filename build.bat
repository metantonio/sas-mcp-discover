@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ========================================================
echo           SAS Agent - Project Build
echo ========================================================

set "VENV_DIR=.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PYI=%VENV_DIR%\Scripts\pyinstaller.exe"

if not exist "%VENV_PY%" (
    echo [1/3] Virtual environment not found. Creating %VENV_DIR%...
    
    where py >nul 2>&1
    if !ERRORLEVEL! equ 0 (
        py -3.11 -m venv %VENV_DIR% >nul 2>&1
        if not exist "%VENV_PY%" (
            py -3 -m venv %VENV_DIR%
        )
    ) else (
        where python >nul 2>&1
        if !ERRORLEVEL! equ 0 (
            python -m venv %VENV_DIR%
        ) else (
            echo ERROR: No Python interpreter found on the system.
            pause
            exit /b 1
        )
    )

    if not exist "%VENV_PY%" (
        echo ERROR: Failed to initialize virtual environment.
        pause
        exit /b 1
    )

    echo [2/3] Installing dependencies from requirements.txt...
    "%VENV_PY%" -m pip install --upgrade pip
    "%VENV_PY%" -m pip install -r requirements.txt
    if !ERRORLEVEL! neq 0 (
        echo ERROR: An error occurred while installing dependencies.
        pause
        exit /b 1
    )
) else (
    echo [1/3] Existing virtual environment detected at %VENV_DIR%.
    echo [2/3] Verifying dependencies from requirements.txt...
    "%VENV_PY%" -m pip install -r requirements.txt
    if !ERRORLEVEL! neq 0 (
        echo ERROR: An error occurred while verifying dependencies.
        pause
        exit /b 1
    )
)

echo [3/3] Bundling SASAgent.exe with PyInstaller...
"%VENV_PYI%" --noconfirm --clean --onefile --name SASAgent --collect-all mcp --collect-all httpx2 app.py
if !ERRORLEVEL! neq 0 (
    echo ERROR: An error occurred during compilation.
    pause
    exit /b 1
)

if exist config.json (
    if not exist dist mkdir dist
    copy /y config.json dist\config.json >nul
    echo Configuration file copied to dist\config.json.
)

echo.
echo ========================================================
echo   BUILD SUCCESSFUL: dist\SASAgent.exe
echo ========================================================
echo.
pause
