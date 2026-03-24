@echo off
setlocal

echo ======================================================================
echo Starting GitHub Actions Matrix Duplication
echo ======================================================================

echo [1/7] Running Win MSVC 2026 variations...
call "%~dp0build_msvc2026.cmd"
if errorlevel 1 goto :error

echo [2/7] Running Win MSVC 2022 variations...
call "%~dp0build_msvc2022.cmd"
if errorlevel 1 goto :error

echo [3/7] Running Win MSVC 2005 variation...
call "%~dp0build_msvc2005.cmd"
if errorlevel 1 goto :error

echo [4/7] Running Win MinGW variations...
call "%~dp0build_mingw.cmd"
if errorlevel 1 goto :error

echo [5/7] Running Win Cygwin variation...
call "%~dp0build_cygwin.cmd"
if errorlevel 1 goto :error



exit /b 0

:error
exit /b 1

