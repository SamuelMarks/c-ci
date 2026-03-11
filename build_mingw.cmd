@echo off
setlocal
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

echo ======================================================================
echo Win MinGW ^| Shared Lib ^| ANSI ^| Multi-thread ^| LTO OFF ^| System
echo ======================================================================
set "BUILD_DIR=%CD%\build_mingw_shared"
cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=ANSI -DCDD_THREADING=ON -DCDD_DEPS=SYSTEM -DCDD_MSVC_RTC=OFF
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --parallel 4
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo ======================================================================
echo Win MinGW ^| Static Lib ^| Unicode ^| Single-thread ^| LTO ON ^| FetchContent
echo ======================================================================
set "BUILD_DIR=%CD%\build_mingw_static"
cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON -DCDD_CHARSET=UNICODE -DCDD_THREADING=OFF -DCDD_DEPS=FETCHCONTENT -DCDD_MSVC_RTC=OFF
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --parallel 4
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo MinGW variations completed successfully.
