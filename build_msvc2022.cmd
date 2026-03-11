@echo off
setlocal
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

echo ======================================================================
echo Win MSVC 2022 ^| Shared Lib (MTd) ^| ANSI ^| LTO OFF ^| Single-thread ^| FetchContent ^| RTCs
echo ======================================================================
set "BUILD_DIR=%CD%\build_msvc2022_shared"
cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "Visual Studio 17 2022" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=ANSI -DCDD_THREADING=OFF -DCDD_DEPS=FETCHCONTENT -DCDD_MSVC_RTC=RTCs -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebug
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%" --parallel 4
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"
set PATH=%BUILD_DIR%\%BUILD_TYPE%;%BUILD_DIR%\_deps\c89stringutils-build\%BUILD_TYPE%;%BUILD_DIR%\_deps\c_abstract_http-build\%BUILD_TYPE%;%PATH%
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo MSVC 2022 variation completed successfully.
