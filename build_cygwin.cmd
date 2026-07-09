@echo off
setlocal EnableDelayedExpansion
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

where gcc >nul 2>nul
if errorlevel 1 (
    if exist "C:\usr\cygwin64\bin\gcc.exe" (
        set "PATH=C:\usr\cygwin64\bin;%PATH%"
    ) else if exist "C:\cygwin\bin\gcc.exe" (
        set "PATH=C:\cygwin\bin;%PATH%"
    ) else if exist "C:\tools\cygwin\bin\gcc.exe" (
        set "PATH=C:\tools\cygwin\bin;%PATH%"
    ) else (
        echo Error: gcc not found in PATH or common Cygwin locations.
        exit /b 0
    )
)

set "SHELLOPTS=igncr"

echo ======================================================================
echo Win Cygwin ^| Static Lib ^| Unicode ^| Single-thread ^| LTO OFF ^| FetchContent
echo ======================================================================
set "BUILD_DIR=build_cygwin_static"

set "FETCH_ARGS="
if exist "..\parson" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_PARSON="%SRC_DIR%\..\parson"
if exist "..\c-abstract-http" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_C-ABSTRACT-HTTP="%SRC_DIR%\..\c-abstract-http"
if exist "..\c89stringutils" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_C89STRINGUTILS="%SRC_DIR%\..\c89stringutils"
if exist "..\cdd-c" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_CDD-C="%SRC_DIR%\..\cdd-c"
if exist "..\c-str-span" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_C-STR-SPAN="%SRC_DIR%\..\c-str-span"
if exist "..\c-orm" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_C-ORM="%SRC_DIR%\..\c-orm"
if exist "..\cfs" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_CFS="%SRC_DIR%\..\cfs"

cmake -S . -B "%BUILD_DIR%" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=UNICODE -DCDD_THREADING=OFF -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF !FETCH_ARGS! %*
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%" --parallel 4
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"

set "EXTRA_PATH="
if exist "_deps" (
    for /d %%D in ("_deps\*-build") do (
        set "EXTRA_PATH=!EXTRA_PATH!;%%D\"
    )
)
set "PATH=%BUILD_DIR%\!EXTRA_PATH!;%PATH%"

ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo Cygwin variation completed successfully.
