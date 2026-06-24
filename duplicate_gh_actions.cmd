@echo off
setlocal
set "VCPKG_INSTALLATION_ROOT="
set "VCPKG_ROOT=C:\Users\samue\repos\vcpkg"
call "%~dp0build_msvc2026.cmd" %*
if errorlevel 1 goto :error
call "%~dp0build_msvc2022.cmd" %*
if errorlevel 1 goto :error
call "%~dp0build_msvc2005.cmd" %*
if errorlevel 1 goto :error
call "%~dp0build_mingw.cmd" %*
if errorlevel 1 goto :error
call "%~dp0build_cygwin.cmd" %*
if errorlevel 1 goto :error
exit /b 0
:error
exit /b 1
