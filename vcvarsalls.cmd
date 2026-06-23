@echo off
if defined VSCMD_VER goto already_set
if defined VS80COMNTOOLS goto setup_2005

:setup_latest
:: Find latest Visual Studio (2022 or 2019)
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" set "VSWHERE=%ProgramFiles%\Microsoft Visual Studio\Installer\vswhere.exe"
if not exist "%VSWHERE%" goto setup_2005

for /f "usebackq tokens=*" %%i in ("%VSWHERE%" -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath) do (
  set "VS_PATH=%%i"
)

if not defined VS_PATH goto setup_2005

echo Setting up MSVC environment (Latest)...
call "%VS_PATH%\VC\Auxiliary\Build\vcvarsall.bat" x64
goto :eof

:setup_2005
if not defined VS80COMNTOOLS (
    echo Error: Could not find any Visual Studio installation.
    echo Please ensure Visual Studio is installed.
    exit /b 1
)

echo Setting up MSVC 2005 environment...
call "%VS80COMNTOOLS%vsvars32.bat"
goto :eof

:already_set
echo MSVC environment already configured.
goto :eof
