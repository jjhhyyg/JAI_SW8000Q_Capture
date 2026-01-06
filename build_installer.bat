@echo off
REM Build NSIS Installer for JAI SW-8000Q Capture
REM Requires NSIS to be installed and in PATH

echo Building JAI SW-8000Q Capture Installer...
echo.

REM Check if NSIS is available
where makensis >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: NSIS not found in PATH
    echo Please install NSIS from https://nsis.sourceforge.io/
    echo Or add NSIS installation directory to PATH
    pause
    exit /b 1
)

REM Check if main.dist exists
if not exist "main.dist" (
    echo ERROR: main.dist folder not found
    echo Please run nuitka/pyinstaller to create the distribution first
    pause
    exit /b 1
)

REM Check if dependencies folder exists
if not exist "dependencies" (
    echo ERROR: dependencies folder not found
    echo Please create dependencies folder and add the eBUS SDK installer to it
    pause
    exit /b 1
)

REM Compile the installer
echo Compiling installer...
makensis installer.nsi

if %ERRORLEVEL% equ 0 (
    echo.
    echo SUCCESS: JAI_SW8000Q_Capture_Setup.exe created
) else (
    echo.
    echo ERROR: Failed to create installer
)

pause
