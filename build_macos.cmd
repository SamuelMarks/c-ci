@echo off
setlocal EnableDelayedExpansion

set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

echo ======================================================================
echo macOS Clang ^| Shared Lib ^| Unicode ^| Multi-thread ^| LTO ON ^| FetchContent
echo ======================================================================
echo Note: This script is the Windows batch equivalent of build_macos.sh.
echo It attempts to run a macOS-like build configuration locally.

set "BUILD_DIR=%SRC_DIR%\build_macos_shared"

cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON -DCDD_CHARSET=UNICODE -DCDD_THREADING=ON -DCDD_DEPS=FETCHCONTENT -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF %*
if errorlevel 1 exit /b 1

cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%" --parallel 4
if errorlevel 1 exit /b 1

pushd "%BUILD_DIR%"
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo ======================================================================
echo macOS Clang ^| Static Lib ^| ANSI ^| Single-thread ^| LTO OFF ^| System
echo ======================================================================
set "BUILD_DIR=%SRC_DIR%\build_macos_static"

cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=ANSI -DCDD_THREADING=OFF -DCDD_DEPS=SYSTEM -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF %*
if errorlevel 1 exit /b 1

cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%" --parallel 4
if errorlevel 1 exit /b 1

pushd "%BUILD_DIR%"
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo macOS variations completed successfully.
