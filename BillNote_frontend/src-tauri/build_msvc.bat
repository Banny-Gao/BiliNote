@echo off
set PATH=C:\Users\Administrator\.cargo\bin;%PATH%
call "C:\VS2022BuildTools\VC\Auxiliary\Build\vcvars64.bat"
cd /d "%~dp0.."
echo Cleaning old build artifacts...
if exist src-tauri\target\release rmdir /s /q src-tauri\target\release
echo Building with MSVC environment...
pnpm tauri build
if %ERRORLEVEL% NEQ 0 (
    echo Build failed with error code %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)
