@echo off
setlocal EnableDelayedExpansion
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

call "%~dp0vcvarsalls.cmd" 2005
if errorlevel 1 exit /b 1

echo ======================================================================
echo Win MSVC 2005 ^| Static Lib (MTd) ^| LTO OFF ^| Multi-thread ^| RTCs
echo ======================================================================
set "BUILD_DIR=%CD%\build_msvc2005_static"

echo @echo off> "%BUILD_DIR%_cmake_call.cmd"
echo set "FETCH_ARGS=">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\parson" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_PARSON="%SRC_DIR%\..\parson">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c-abstract-http" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C-ABSTRACT-HTTP="%SRC_DIR%\..\c-abstract-http">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c89stringutils" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C89STRINGUTILS="%SRC_DIR%\..\c89stringutils">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\cdd-c" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_CDD-C="%SRC_DIR%\..\cdd-c">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c-str-span" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C-STR-SPAN="%SRC_DIR%\..\c-str-span">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\c-orm" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C-ORM="%SRC_DIR%\..\c-orm">> "%BUILD_DIR%_cmake_call.cmd"
if exist "..\cfs" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_CFS="%SRC_DIR%\..\cfs">> "%BUILD_DIR%_cmake_call.cmd"

echo cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=%BUILD_TYPE% -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DBUILD_TESTING=ON -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebug %%FETCH_ARGS%% %%*>> "%BUILD_DIR%_cmake_call.cmd"

call "%BUILD_DIR%_cmake_call.cmd" %*
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%"
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"

set "EXTRA_PATH="
if exist "_deps" (
    for /d %%D in ("_deps\*-build") do (
        set "EXTRA_PATH=!EXTRA_PATH!;%%D\%BUILD_TYPE%"
    )
)
set "PATH=%BUILD_DIR%\%BUILD_TYPE%!EXTRA_PATH!;%PATH%"

ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo MSVC 2005 variation completed successfully.
