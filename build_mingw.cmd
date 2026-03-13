@echo off
setlocal
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
cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=ANSI -DCDD_THREADING=ON -DCDD_DEPS=SYSTEM -DC_CDD_BUILD_TESTING=ON -DC_ORM_BUILD_TESTING=ON -DC_ABSTRACT_HTTP_BUILD_TESTING=ON -DC_FS_BUILD_TESTING=ON -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF -DCMAKE_C_FLAGS_INIT=-D_GNU_SOURCE -DCMAKE_CXX_FLAGS_INIT=-D_GNU_SOURCE
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%" --parallel 4
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"
set PATH=%BUILD_DIR%\;%BUILD_DIR%\_deps\c89stringutils-build\;%BUILD_DIR%\_deps\c_abstract_http-build\;%PATH%
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo ======================================================================
echo Win MinGW ^| Static Lib ^| Unicode ^| Single-thread ^| LTO ON ^| FetchContent
echo ======================================================================
set "BUILD_DIR=%CD%\build_mingw_static"
cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON -DCDD_CHARSET=UNICODE -DCDD_THREADING=OFF -DCDD_DEPS=FETCHCONTENT -DC_CDD_BUILD_TESTING=ON -DC_ORM_BUILD_TESTING=ON -DC_ABSTRACT_HTTP_BUILD_TESTING=ON -DC_FS_BUILD_TESTING=ON -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF -DCMAKE_C_FLAGS_INIT=-D_GNU_SOURCE -DCMAKE_CXX_FLAGS_INIT=-D_GNU_SOURCE
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%" --parallel 4
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"
set PATH=%BUILD_DIR%\;%BUILD_DIR%\_deps\c89stringutils-build\;%BUILD_DIR%\_deps\c_abstract_http-build\;%PATH%
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo MinGW variations completed successfully.
