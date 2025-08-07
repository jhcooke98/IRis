@echo off
REM Build and Deploy Script for IR Remote Mini Firmware (Windows)
REM This script compiles the Arduino firmware and copies it to the firmware directory

setlocal enabledelayedexpansion

REM Configuration
set "ARDUINO_CLI_PATH=arduino-cli.exe"
set "BOARD=esp32:esp32:esp32"
set "SKETCH_DIR=.\arduino_project"
set "FIRMWARE_DIR=.\firmware"
set "VERSION_FILE=version.txt"

REM Check if arduino-cli is installed
where %ARDUINO_CLI_PATH% >nul 2>&1
if errorlevel 1 (
    echo [ERROR] arduino-cli not found. Please install it first.
    echo Download from: https://arduino.github.io/arduino-cli/latest/installation/
    pause
    exit /b 1
)
echo [SUCCESS] arduino-cli found

REM Check if sketch directory exists
if not exist "%SKETCH_DIR%" (
    echo [ERROR] Sketch directory not found: %SKETCH_DIR%
    echo Please update SKETCH_DIR in this script to point to your Arduino project
    pause
    exit /b 1
)
echo [SUCCESS] Sketch directory found: %SKETCH_DIR%

REM Get current version
if exist "%VERSION_FILE%" (
    set /p CURRENT_VERSION=<%VERSION_FILE%
    echo [INFO] Current version: !CURRENT_VERSION!
    
    REM Parse version for suggestion
    for /f "tokens=1,2,3 delims=." %%a in ("!CURRENT_VERSION!") do (
        set MAJOR=%%a
        set MINOR=%%b
        set /a PATCH=%%c+1
    )
    set "SUGGESTED_VERSION=!MAJOR!.!MINOR!.!PATCH!"
    
    set /p "NEW_VERSION=Enter new version [!SUGGESTED_VERSION!]: "
    if "!NEW_VERSION!"=="" set "NEW_VERSION=!SUGGESTED_VERSION!"
) else (
    set /p "NEW_VERSION=Enter firmware version (e.g., 1.0.0): "
)

echo [INFO] Building version: %NEW_VERSION%

REM Update version in Arduino code
set "VERSION_HEADER=%SKETCH_DIR%\version.h"
(
echo #ifndef VERSION_H
echo #define VERSION_H
echo.
echo #define FIRMWARE_VERSION "%NEW_VERSION%"
echo.
echo #endif
) > "%VERSION_HEADER%"

echo [SUCCESS] Updated version.h with version %NEW_VERSION%

REM Find the main sketch file
for %%f in ("%SKETCH_DIR%\*.ino") do (
    set "SKETCH_FILE=%%f"
    goto :found_sketch
)
echo [ERROR] No .ino file found in %SKETCH_DIR%
pause
exit /b 1

:found_sketch
echo [INFO] Compiling sketch: %SKETCH_FILE%

REM Compile the sketch
%ARDUINO_CLI_PATH% compile --fqbn %BOARD% "%SKETCH_FILE%" --output-dir "%SKETCH_DIR%\build"
if errorlevel 1 (
    echo [ERROR] Compilation failed
    pause
    exit /b 1
)
echo [SUCCESS] Compilation successful

REM Deploy firmware
echo [INFO] Deploying firmware to repository...

REM Create firmware directory if it doesn't exist
if not exist "%FIRMWARE_DIR%" mkdir "%FIRMWARE_DIR%"

REM Find the compiled binary
for %%f in ("%SKETCH_DIR%\build\*.bin") do (
    set "BINARY_FILE=%%f"
    goto :found_binary
)
echo [ERROR] No .bin file found in build directory
pause
exit /b 1

:found_binary
set "FIRMWARE_FILENAME=ir_remote_v%NEW_VERSION%.bin"
set "FIRMWARE_PATH=%FIRMWARE_DIR%\%FIRMWARE_FILENAME%"

copy "%BINARY_FILE%" "%FIRMWARE_PATH%" >nul
if errorlevel 1 (
    echo [ERROR] Failed to deploy firmware
    pause
    exit /b 1
)

echo [SUCCESS] Firmware deployed: %FIRMWARE_PATH%

REM Update version file
echo %NEW_VERSION% > "%VERSION_FILE%"

REM Get file size
for %%f in ("%FIRMWARE_PATH%") do set FILE_SIZE=%%~zf
echo [INFO] Firmware size: %FILE_SIZE% bytes

REM Create symlink to latest (optional)
if exist "%FIRMWARE_DIR%\latest.bin" del "%FIRMWARE_DIR%\latest.bin"
mklink "%FIRMWARE_DIR%\latest.bin" "%FIRMWARE_FILENAME%" >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Created symlink: latest.bin -^> %FIRMWARE_FILENAME%
)

REM Git operations (optional)
if exist ".git" (
    choice /m "Commit changes to git"
    if !errorlevel!==1 (
        git add "%FIRMWARE_PATH%" "%VERSION_FILE%"
        git commit -m "Release firmware v%NEW_VERSION%"
        echo [SUCCESS] Changes committed to git
        
        choice /m "Create git tag v%NEW_VERSION%"
        if !errorlevel!==1 (
            git tag "v%NEW_VERSION%"
            echo [SUCCESS] Created git tag v%NEW_VERSION%
        )
    )
)

REM Cleanup
choice /m "Clean build directory"
if !errorlevel!==1 (
    if exist "%SKETCH_DIR%\build" (
        rmdir /s /q "%SKETCH_DIR%\build"
        echo [SUCCESS] Build directory cleaned
    )
)

REM Summary
echo.
echo [SUCCESS] Build and deployment complete!
echo ==========================
echo Version: %NEW_VERSION%
echo Firmware: %FIRMWARE_PATH%
echo Size: %FILE_SIZE% bytes
echo.
echo Next steps:
echo 1. Test the firmware on a single device
echo 2. Use Home Assistant integration to deploy updates
echo 3. Monitor device status after update
echo.

pause
