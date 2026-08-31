@echo off
setlocal enabledelayedexpansion

title FormulaPy v1.0.0 Setup

echo.
echo  ==========================================
echo    FormulaPy v1.0.0 Setup
echo  ==========================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Please run as Administrator!
    echo Right-click install.bat ^> "Run as administrator"
    pause
    exit /b 1
)

set "INSTALL_DIR=%LOCALAPPDATA%\FormulaPy\Engine"

echo [INFO] Checking winget...
winget --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARN] winget not found. Installing...
    powershell -Command "$progressPreference = 'silentlyContinue'; Install-PackageProvider -Name NuGet -Force | Out-Null; Install-Module -Name Microsoft.WinGet.Client -Force -Repository PSGallery | Out-Null; Repair-WinGetPackageManager -AllUsers"
    echo [OK] winget installed.
)

echo [INFO] Checking Python...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARN] Python not found.
    set /p install_python="Install Python 3.11 via winget? (y/n): "
    if /i "!install_python!"=="y" (
        echo [INFO] Installing Python 3.11...
        winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
        
        echo [INFO] Refreshing PATH...
        for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYS_PATH=%%B"
        for /f "tokens=2*" %%A in ('reg query "HKCU\Environment" /v Path 2^>nul') do set "USR_PATH=%%B"
        set "PATH=%SYS_PATH%;%USR_PATH%"
        
        where python >nul 2>&1
        if !errorLevel! neq 0 (
            set "PYTHON_DIR=%LOCALAPPDATA%\Programs\Python\Python311"
            set "PYTHON_SCRIPTS=%LOCALAPPDATA%\Programs\Python\Python311\Scripts"
            set "PATH=%PATH%;%PYTHON_DIR%;%PYTHON_SCRIPTS%"
        )
        
        echo [OK] Python installed and PATH updated.
    ) else (
        echo [ERROR] Python is required for FormulaPy.
        pause
        exit /b 1
    )
) else (
    echo [OK] Python found.
)

echo.
echo [INFO] Checking dependencies...
python -c "import numba, colorama, requests" >nul 2>&1
if %errorLevel% neq 0 (
    echo [WARN] Missing dependencies. (If you need dependencies, restart install.bat.)
    set /p install_deps="Install dependencies via pip? (y/n): "
    if /i "!install_deps!"=="y" (
        echo [INFO] Installing dependencies...
        python -m pip install numba numpy colorama requests
        if !errorLevel! neq 0 (
            echo [ERROR] Dependency installation failed.
            pause
            exit /b 1
        )
        echo [OK] Dependencies installed.
    ) else (
        echo [WARN] Skipping dependencies. FormulaPy may not work correctly.
    )
) else (
    echo [OK] Dependencies found.
)

echo.
echo [INFO] Creating directories...
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

echo [INFO] Copying files...
if not exist "%~dp0formulapy.py" (
    echo [ERROR] formulapy.py not found!
    pause
    exit /b 1
)
if not exist "%~dp0formulacore.dll" (
    echo [ERROR] formulacore.dll not found!
    pause
    exit /b 1
)

copy /Y "%~dp0formulapy.py" "%INSTALL_DIR%\formulapy.py" >nul
copy /Y "%~dp0formulacore.dll" "%INSTALL_DIR%\formulacore.dll" >nul
echo [OK] Files copied.

echo [INFO] Creating formulapy.bat...
(
    echo @echo off
    echo python "%INSTALL_DIR%\formulapy.py" %%*
) > "%INSTALL_DIR%\formulapy.bat"
echo [OK] formulapy.bat created.

echo.
set /p add_path="Add FormulaPy to PATH? (y/n): "
if /i "!add_path!"=="y" (
    echo [INFO] Adding to PATH...
    powershell -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'User') + ';%INSTALL_DIR%', 'User')"
    set "PATH=%PATH%;%INSTALL_DIR%"
    echo [OK] Added to PATH.
) else (
    echo [WARN] Skipping PATH.
)

echo.
echo  ==========================================
echo    FormulaPy installed successfully!
echo  ==========================================
echo.
echo  Usage:
echo    formulapy script.py
echo.
echo  NOTE: Restart console if command not found.
echo.
pause