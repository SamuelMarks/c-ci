@echo off
setlocal EnableDelayedExpansion
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"
where gcc >nul 2>nul
if errorlevel 1 (
    if exist "C:\msys64\ucrt64\bin\gcc.exe" (
        set "PATH=C:\msys64\ucrt64\bin;%PATH%"
    ) else if exist "C:\msys64\mingw64\bin\gcc.exe" (
        set CMAKE_C_COMPILER="C:\msys64\mingw64\bin\gcc.exe"
        set "PATH=C:\msys64\mingw64\bin;%PATH%"
    ) else if exist "C:\msys64\mingw32\bin\gcc.exe" (
        set "PATH=C:\msys64\mingw32\bin;%PATH%"
    ) else if exist "C:\MinGW\bin\gcc.exe" (
        set "PATH=C:\MinGW\bin;%PATH%"
    ) else if exist "C:\Strawberry\c\bin\gcc.exe" (
        set "PATH=C:\Strawberry\c\bin;%PATH%"
    ) else if exist "C:\TDM-GCC-64\bin\gcc.exe" (
        set "PATH=C:\TDM-GCC-64\bin;%PATH%"
    ) else (
        echo Error: gcc not found in PATH or common locations.
        exit /b 2
    )
)


echo ======================================================================
echo Win MinGW ^| Shared Lib ^| ANSI ^| Multi-thread ^| LTO OFF ^| System
echo ======================================================================
set "BUILD_DIR=%CD%\build_mingw_shared"
cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=ANSI -DCDD_THREADING=ON -DCDD_DEPS=SYSTEM -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF %*
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

echo ======================================================================
echo Win MinGW ^| Static Lib ^| Unicode ^| Single-thread ^| LTO ON ^| FetchContent
echo ======================================================================
set "BUILD_DIR=%CD%\build_mingw_static"

set "FETCH_ARGS="
if exist "..\parson" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_PARSON="%SRC_DIR%\..\parson"
if exist "..\c-abstract-http" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_C_ABSTRACT_HTTP="%SRC_DIR%\..\c-abstract-http"
if exist "..\c89stringutils" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_C89STRINGUTILS="%SRC_DIR%\..\c89stringutils"
if exist "..\cdd-c" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_CDD_C="%SRC_DIR%\..\cdd-c"
if exist "..\c-str-span" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_C_STR_SPAN="%SRC_DIR%\..\c-str-span"
if exist "..\c-orm" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_C_ORM="%SRC_DIR%\..\c-orm"
if exist "..\cfs" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_CFS="%SRC_DIR%\..\cfs"

cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON -DCDD_CHARSET=UNICODE -DCDD_THREADING=OFF -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF !FETCH_ARGS! %*
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

echo MinGW variations completed successfully.
