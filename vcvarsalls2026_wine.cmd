@echo off
if defined MSVC_2026_WINE_SET goto already_set

echo Setting up MSVC 2026 Wine environment...

set "WINEDLLOVERRIDES=vcruntime140=n;vcruntime140_1=n"
set "MSVC_DIR=Z:\home\samuel\my_msvc\opt\msvc\VC\Tools\MSVC\14.51.36231"
set "SDK_DIR=Z:\home\samuel\my_msvc\opt\msvc\kits\10"
set "SDK_VER=10.0.26100.0"

set "LIBPATH=%MSVC_DIR%\atlmfc\lib\x64;%MSVC_DIR%\lib\x64;%SDK_DIR%\Lib\%SDK_VER%\ucrt\x64;%SDK_DIR%\Lib\%SDK_VER%\um\x64;%SDK_DIR%\Lib\%SDK_VER%\km\x64"
set "INCLUDE=%MSVC_DIR%\atlmfc\include;%MSVC_DIR%\include;%SDK_DIR%\Include\%SDK_VER%\shared;%SDK_DIR%\Include\%SDK_VER%\ucrt;%SDK_DIR%\Include\%SDK_VER%\um;%SDK_DIR%\Include\%SDK_VER%\winrt;%SDK_DIR%\Include\%SDK_VER%\km"
set "CMAKE_BIN=C:\Program Files\CMake\bin"
:: BYPASS WINDOWS GIT ENTIRELY! It hangs on submodule. Instead we use the host git!
set "GIT_BIN="
set "GIT_TERMINAL_PROMPT=0"

set "PATH=%CMAKE_BIN%;%MSVC_DIR%\bin\Hostx64\x64;%SDK_DIR%\bin\%SDK_VER%\x64;Z:\usr\bin;%PATH%"
set "LIB=%MSVC_DIR%\atlmfc\lib\x64;%MSVC_DIR%\lib\x64;%SDK_DIR%\Lib\%SDK_VER%\ucrt\x64;%SDK_DIR%\Lib\%SDK_VER%\um\x64;%SDK_DIR%\Lib\%SDK_VER%\km\x64"

set "MSVC_2026_WINE_SET=1"
goto :eof

:already_set
echo MSVC 2026 Wine environment already configured.
goto :eof
