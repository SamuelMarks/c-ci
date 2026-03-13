@echo off
setlocal
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

where gcc >nul 2>nul
if errorlevel 1 (
    if exist "C:\cygwin64\bin\gcc.exe" (
        set "PATH=C:\cygwin64\bin;%PATH%"
    ) else if exist "C:\cygwin\bin\gcc.exe" (
        set "PATH=C:\cygwin\bin;%PATH%"
    ) else if exist "C:\tools\cygwin\bin\gcc.exe" (
        set "PATH=C:\tools\cygwin\bin;%PATH%"
    ) else (
        echo Error: gcc not found in PATH or common Cygwin locations.
        exit /b 2
    )
)

set "SHELLOPTS=igncr"

echo ======================================================================
echo Win Cygwin ^| Static Lib ^| Unicode ^| Single-thread ^| LTO OFF ^| FetchContent
echo ======================================================================
set "BUILD_DIR=%CD%\build_cygwin_static"
cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "Unix Makefiles" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=UNICODE -DCDD_THREADING=OFF -DCDD_DEPS=FETCHCONTENT -DC_CDD_BUILD_TESTING=ON -DC_ORM_BUILD_TESTING=ON -DC_ABSTRACT_HTTP_BUILD_TESTING=ON -DC_FS_BUILD_TESTING=ON -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF -DCMAKE_C_FLAGS_INIT=-D_GNU_SOURCE -DCMAKE_CXX_FLAGS_INIT=-D_GNU_SOURCE
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%" --parallel 4
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"
set "PATH=%BUILD_DIR%;%BUILD_DIR%\_deps\c89stringutils-build;%BUILD_DIR%\_deps\c_abstract_http-build;%PATH%"
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo Cygwin variation completed successfully.
