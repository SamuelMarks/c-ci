@echo off
setlocal
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

echo ======================================================================
echo Win MSVC Latest ^| Shared Lib (MD) ^| Unicode ^| LTO OFF ^| Multi-thread ^| FetchContent
echo ======================================================================
set "BUILD_DIR=%CD%\build_msvc2026_shared"
cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "Visual Studio 18 2026" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=UNICODE -DCDD_THREADING=ON -DCDD_DEPS=FETCHCONTENT -DC_CDD_BUILD_TESTING=ON -DC_ORM_BUILD_TESTING=ON -DC_ABSTRACT_HTTP_BUILD_TESTING=ON -DC_FS_BUILD_TESTING=ON -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%" --parallel 4
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"
set PATH=%BUILD_DIR%\%BUILD_TYPE%;%BUILD_DIR%\_deps\c89stringutils-build\%BUILD_TYPE%;%BUILD_DIR%\_deps\c_abstract_http-build\%BUILD_TYPE%;%PATH%
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo ======================================================================
echo Win MSVC Latest ^| Static Lib (MT) ^| ANSI ^| LTO ON ^| Single-thread ^| Vcpkg ^| RTC1
echo ======================================================================
set "BUILD_DIR=%CD%\build_msvc2026_static_vcpkg"

if not defined VCPKG_INSTALLATION_ROOT if not defined VCPKG_ROOT (
    if not exist "%CD%\vcpkg" (
        echo Cloning vcpkg ^(offscale/vcpkg branch project0^)...
        git clone --branch project0 https://github.com/offscale/vcpkg.git "%CD%\vcpkg"
        call "%CD%\vcpkg\bootstrap-vcpkg.bat" -disableMetrics
    )
    set "VCPKG_ROOT=%CD%\vcpkg"
)

set "CMAKE_EXTRA_ARGS="
if defined NO_VCPKG_INSTALLATION_ROOT (
  set "CMAKE_EXTRA_ARGS=-DCMAKE_TOOLCHAIN_FILE=%VCPKG_INSTALLATION_ROOT%/scripts/buildsystems/vcpkg.cmake"
) else if defined VCPKG_ROOT (
  set "CMAKE_EXTRA_ARGS=-DCMAKE_TOOLCHAIN_FILE=%VCPKG_ROOT%/scripts/buildsystems/vcpkg.cmake"
)

cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "Visual Studio 18 2026" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON -DCDD_CHARSET=ANSI -DCDD_THREADING=OFF -DCDD_DEPS=FETCHCONTENT -DC_CDD_BUILD_TESTING=ON -DC_ORM_BUILD_TESTING=ON -DC_ABSTRACT_HTTP_BUILD_TESTING=ON -DC_FS_BUILD_TESTING=ON -DBUILD_TESTING=ON -DCDD_MSVC_RTC=RTC1 -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded %CMAKE_EXTRA_ARGS%
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%" --parallel 4
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"
set PATH=%BUILD_DIR%\%BUILD_TYPE%;%BUILD_DIR%\_deps\c89stringutils-build\%BUILD_TYPE%;%BUILD_DIR%\_deps\c_abstract_http-build\%BUILD_TYPE%;%PATH%
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo ======================================================================
echo Win MSVC Latest ^| Static Lib (MDd) ^| Unicode ^| LTO OFF ^| Multi-thread ^| System ^| RTCu
echo ======================================================================
set "BUILD_DIR=%CD%\build_msvc2026_static_system"
cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -G "Visual Studio 18 2026" -DCMAKE_BUILD_TYPE="%BUILD_TYPE%" -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=UNICODE -DCDD_THREADING=ON -DCDD_DEPS=SYSTEM -DC_CDD_BUILD_TESTING=ON -DC_ORM_BUILD_TESTING=ON -DC_ABSTRACT_HTTP_BUILD_TESTING=ON -DC_FS_BUILD_TESTING=ON -DBUILD_TESTING=ON -DCDD_MSVC_RTC=RTCu -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebugDLL
if errorlevel 1 exit /b 1
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%" --parallel 4
if errorlevel 1 exit /b 1
pushd "%BUILD_DIR%"
set PATH=%BUILD_DIR%\%BUILD_TYPE%;%BUILD_DIR%\_deps\c89stringutils-build\%BUILD_TYPE%;%BUILD_DIR%\_deps\c_abstract_http-build\%BUILD_TYPE%;%PATH%
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 exit /b 1
popd

echo All MSVC 2026 variations completed successfully.
