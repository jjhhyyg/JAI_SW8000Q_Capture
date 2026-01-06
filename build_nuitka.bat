@echo off
REM Build JAI SW-8000Q Capture with Nuitka
REM This script compiles the application and includes all necessary data files

echo Building JAI SW-8000Q Capture with Nuitka...
echo.

REM Check if nuitka is available
where nuitka >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Nuitka not found in PATH
    echo Please install Nuitka: pip install nuitka
    pause
    exit /b 1
)

REM Clean previous build
if exist "main.dist" (
    echo Removing previous build...
    rmdir /s /q main.dist
)
if exist "main.build" (
    rmdir /s /q main.build
)

REM Build with Nuitka
echo Compiling with Nuitka...
python -m nuitka ^
    --standalone ^
    --windows-console-mode=disable ^
    --enable-plugin=pyside6 ^
    --include-data-dir=translations=translations ^
    --output-dir=. ^
    --windows-icon-from-ico=icon.ico ^
    main.py

if %ERRORLEVEL% equ 0 (
    echo.
    echo SUCCESS: Build completed
    echo Output: main.dist\main.exe
    echo.
    echo Note: The translations folder has been included in main.dist\translations
) else (
    echo.
    echo ERROR: Build failed
)

pause
