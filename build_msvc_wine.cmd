@echo off
setlocal EnableDelayedExpansion

set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

:: On Windows natively, we don't use wine. We just configure the native MSVC environment.
call "%~dp0vcvarsalls.cmd" latest
if errorlevel 1 exit /b 1

set "FETCH_ARGS="
if exist "..\parson" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_PARSON="%SRC_DIR%\..\parson"
if exist "..\c-abstract-http" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_C-ABSTRACT-HTTP="%SRC_DIR%\..\c-abstract-http"
if exist "..\c89stringutils" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_C89STRINGUTILS="%SRC_DIR%\..\c89stringutils"
if exist "..\cdd-c" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_CDD-C="%SRC_DIR%\..\cdd-c"
if exist "..\c-str-span" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_C-STR-SPAN="%SRC_DIR%\..\c-str-span"
if exist "..\c-orm" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_C-ORM="%SRC_DIR%\..\c-orm"
if exist "..\c-fs" set FETCH_ARGS=!FETCH_ARGS! -DFETCHCONTENT_SOURCE_DIR_CFS="%SRC_DIR%\..\c-fs"

echo ======================================================================
echo MSVC Native (Equivalent) ^| Shared Lib (MDd) ^| LTO OFF ^| Multi-thread ^| RTCs
echo ======================================================================
set "BUILD_DIR=%SRC_DIR%\build_msvc_wine_shared"

cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "NMake Makefiles" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DCMAKE_SYSTEM_NAME=Windows -DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=Embedded -DBUILD_SHARED_LIBS=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DBUILD_TESTING=ON -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebugDLL !FETCH_ARGS! %*
if errorlevel 1 exit /b 1

cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%"
if errorlevel 1 exit /b 1

pushd "%BUILD_DIR%"
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

echo ======================================================================
echo MSVC Native (Equivalent) ^| Static Lib (MTd) ^| LTO OFF ^| Single-thread ^| RTC1
echo ======================================================================
set "BUILD_DIR=%SRC_DIR%\build_msvc_wine_static"

cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "NMake Makefiles" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DCMAKE_SYSTEM_NAME=Windows -DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=Embedded -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DBUILD_TESTING=ON -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebug !FETCH_ARGS! %*
if errorlevel 1 exit /b 1

cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%"
if errorlevel 1 exit /b 1

pushd "%BUILD_DIR%"
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

echo All MSVC-Wine native variations completed successfully.
