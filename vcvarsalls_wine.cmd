@echo off

if defined VCINSTALLDIR goto already_set

echo Setting up MSVC 2005 Wine environment...

:: MSVC 2005 paths from the user's OS1 mount
set "VSINSTALLDIR=Z:\media\samuel\OS1\Program Files (x86)\Microsoft Visual Studio 8"
set "VCINSTALLDIR=Z:\media\samuel\OS1\Program Files (x86)\Microsoft Visual Studio 8\VC"
set "FrameworkDir=Z:\media\samuel\OS1\WINDOWS\Microsoft.NET\Framework"
set "FrameworkVersion=v2.0.50727"
set "FrameworkSDKDir=Z:\media\samuel\OS1\Program Files (x86)\Microsoft Visual Studio 8\SDK\v2.0"
set "DevEnvDir=Z:\media\samuel\OS1\Program Files (x86)\Microsoft Visual Studio 8\Common7\IDE"

:: CMake (installed in Wine) and Git (from OS1 mount)
set "CMAKE_BIN=C:\Program Files\CMake\bin"
:: BYPASS WINDOWS GIT ENTIRELY! It hangs on submodule. Instead we use the host git through wine bash!
set "GIT_BIN="
set "GIT_TERMINAL_PROMPT=0"

set "PATH=%DevEnvDir%;%VCINSTALLDIR%\BIN;%VSINSTALLDIR%\Common7\Tools;%VSINSTALLDIR%\Common7\Tools\bin;%VCINSTALLDIR%\PlatformSDK\bin;%FrameworkSDKDir%\bin;%FrameworkDir%\%FrameworkVersion%;%VCINSTALLDIR%\VCPackages;%CMAKE_BIN%;Z:\usr\bin;%PATH%"
set "INCLUDE=%VCINSTALLDIR%\ATLMFC\INCLUDE;%VCINSTALLDIR%\INCLUDE;%VCINSTALLDIR%\PlatformSDK\include;%FrameworkSDKDir%\include;%INCLUDE%"
set "LIB=%VCINSTALLDIR%\ATLMFC\LIB;%VCINSTALLDIR%\LIB;%VCINSTALLDIR%\PlatformSDK\lib;%FrameworkSDKDir%\lib;%LIB%"
set "LIBPATH=%FrameworkDir%\%FrameworkVersion%;%VCINSTALLDIR%\ATLMFC\LIB"

goto :eof

:already_set
echo MSVC Wine environment already configured.
goto :eof
