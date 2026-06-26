@echo off
setlocal EnableDelayedExpansion
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

call "%~dp0vcvarsalls_wine.cmd"
if errorlevel 1 exit /b 1

:: Ensure ninja.exe is available
where ninja.exe >nul 2>nul
if errorlevel 1 (
    echo Ninja not found in PATH. Downloading ninja-win.zip...
    mkdir "%~dp0ninja-bin" 2>nul
    powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://github.com/ninja-build/ninja/releases/download/v1.11.1/ninja-win.zip' -OutFile '%~dp0ninja-bin\ninja-win.zip'"
    powershell -Command "Expand-Archive -Path '%~dp0ninja-bin\ninja-win.zip' -DestinationPath '%~dp0ninja-bin' -Force"
    set "PATH=%~dp0ninja-bin;%PATH%"
)

echo ======================================================================
echo Win MSVC 2005 Wine ^| Static Lib (MTd) ^| LTO OFF ^| Multi-thread ^| RTCs
echo ======================================================================
set "BUILD_DIR=%CD%\build_msvc2005_wine_static"

echo @echo off> "%BUILD_DIR%_cmake_call.cmd"
echo set "FETCH_ARGS=">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\parson" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_PARSON="%SRC_DIR%\..\parson">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c-abstract-http" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C_ABSTRACT_HTTP="%SRC_DIR%\..\c-abstract-http">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c89stringutils" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C89STRINGUTILS="%SRC_DIR%\..\c89stringutils">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\cdd-c" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_CDD_C="%SRC_DIR%\..\cdd-c">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c-str-span" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C_STR_SPAN="%SRC_DIR%\..\c-str-span">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c-orm" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C_ORM="%SRC_DIR%\..\c-orm">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c-fs" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_CFS="%SRC_DIR%\..\c-fs">> "%BUILD_DIR%_cmake_call.cmd"

echo cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G Ninja -DCMAKE_BUILD_TYPE=%BUILD_TYPE% -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DBUILD_TESTING=ON -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebug %%FETCH_ARGS%% %%*>> "%BUILD_DIR%_cmake_call.cmd"

call "%BUILD_DIR%_cmake_call.cmd" %*
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%"
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"
echo Copying MSVC 2005 debug redistributables...
copy "%VCINSTALLDIR%\redist\Debug_NonRedist\x86\Microsoft.VC80.DebugCRT\*.*" .

set "EXTRA_PATH="
if exist "_deps" (
    for /d %%D in ("_deps\*-build") do (
        set "EXTRA_PATH=!EXTRA_PATH!;%%D"
    )
)
set "PATH=%BUILD_DIR%;!EXTRA_PATH!;%PATH%"

ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo MSVC 2005 Wine variation completed successfully.
