@echo off
setlocal
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"

if not exist "C:\usr\WATCOM\binnt" (
    echo Error: OpenWatcom not found at C:\usr\WATCOM
    exit /b 1
)

echo Setting up OpenWatcom environment...
set WATCOM=C:\usr\WATCOM
set PATH=%WATCOM%\binnt;%WATCOM%\binw;%PATH%
set INCLUDE=%WATCOM%\h;%WATCOM%\h\nt
set EDPATH=%WATCOM%\eddat

echo ======================================================================
echo DOS OpenWatcom ^| Static Lib ^| ANSI
echo ======================================================================
set "BUILD_DIR=%CD%\build_dos_watcom"

cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "Watcom WMake" -DCMAKE_SYSTEM_NAME=DOS -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=ON %*
if errorlevel 1 exit /b 1

cmake --build "%BUILD_DIR%"
if errorlevel 1 exit /b 1

echo Build finished successfully. Not running tests on DOS natively yet.
echo OpenWatcom DOS variation completed successfully.
