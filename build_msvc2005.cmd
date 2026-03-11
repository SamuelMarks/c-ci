@echo off
setlocal
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

if not defined VS80COMNTOOLS (
    echo Error: VS80COMNTOOLS environment variable is not set.
    echo Please ensure Visual Studio 2005 is installed.
    exit /b 1
)

echo Setting up MSVC 2005 environment...
call "%VS80COMNTOOLS%vsvars32.bat"

echo ======================================================================
echo Win MSVC 2005 ^| Static Lib (MTd) ^| ANSI ^| LTO OFF ^| Multi-thread ^| System ^| RTCs
echo ======================================================================
set "BUILD_DIR=%CD%\build_msvc2005_static"
cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "NMake Makefiles" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=ANSI -DCDD_THREADING=ON -DCDD_DEPS=SYSTEM -DCDD_MSVC_RTC=RTCs -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebug
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%"
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"
set PATH=%BUILD_DIR%\%BUILD_TYPE%;%BUILD_DIR%\_deps\c89stringutils-build\%BUILD_TYPE%;%BUILD_DIR%\_deps\c_abstract_http-build\%BUILD_TYPE%;%PATH%
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo MSVC 2005 variation completed successfully.
