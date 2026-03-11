@echo off
setlocal
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

echo ======================================================================
echo Win Cygwin ^| Static Lib ^| Unicode ^| Single-thread ^| LTO OFF ^| FetchContent
echo ======================================================================
set "BUILD_DIR=%CD%\build_cygwin_static"
cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=UNICODE -DCDD_THREADING=OFF -DCDD_DEPS=FETCHCONTENT -DCDD_MSVC_RTC=OFF
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --parallel 4
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"
export PATH=\x22/:/_deps/c89stringutils-build/:/_deps/c_abstract_http-build/:\x22
ctest -C \x22%BUILD_TYPE%\x22 --output-on-failure
if errorlevel 1 exit /b 1
popd

echo Cygwin variation completed successfully.
