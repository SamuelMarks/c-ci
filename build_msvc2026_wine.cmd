@echo off
setlocal EnableDelayedExpansion
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

call "%~dp0vcvarsalls2026_wine.cmd"
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
echo Win MSVC 2026 Wine ^| Shared Lib (MD) ^| Unicode ^| LTO OFF ^| FetchContent
echo ======================================================================
set "BUILD_DIR=%SRC_DIR%\build_msvc2026_wine_shared"

echo @echo off> "%BUILD_DIR%_cmake_call.cmd"
echo set "FETCH_ARGS=">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\parson" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_PARSON="%SRC_DIR%\..\parson">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c-abstract-http" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C-ABSTRACT-HTTP="%SRC_DIR%\..\c-abstract-http">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c89stringutils" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C89STRINGUTILS="%SRC_DIR%\..\c89stringutils">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\cdd-c" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_CDD-C="%SRC_DIR%\..\cdd-c">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c-str-span" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C-STR-SPAN="%SRC_DIR%\..\c-str-span">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c-orm" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C-ORM="%SRC_DIR%\..\c-orm">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c-fs" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_CFS="%SRC_DIR%\..\c-fs">> "%BUILD_DIR%_cmake_call.cmd"

echo cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G Ninja -DCMAKE_BUILD_TYPE=%BUILD_TYPE% -DBUILD_SHARED_LIBS=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=UNICODE -DCDD_THREADING=ON -DCDD_DEPS=FETCHCONTENT -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL -DFETCHCONTENT_UPDATES_DISCONNECTED=ON %%FETCH_ARGS%% %%*>> "%BUILD_DIR%_cmake_call.cmd"

call "%BUILD_DIR%_cmake_call.cmd" %*
if errorlevel 1 goto :fail
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%"
if errorlevel 1 goto :fail

set "EXTRA_PATH="
if exist "%BUILD_DIR%\_deps" (
    for /d %%D in ("%BUILD_DIR%\_deps\*-build") do (
        set "EXTRA_PATH=!EXTRA_PATH!;%%D"
    )
)
set "PATH=%BUILD_DIR%;!EXTRA_PATH!;%PATH%"

cd "%BUILD_DIR%"
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 goto :fail

echo MSVC 2026 Wine variation completed successfully.
exit /b 0

:fail
echo Build failed.
exit /b 1
