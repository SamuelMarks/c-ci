@echo off
setlocal enabledelayedexpansion

set "SRC_DIR=%CD%\"
set "SRC_DIR=!SRC_DIR:~0,-1!"

for /f "usebackq tokens=*" %%i in (`powershell -NoProfile -Command "$name = (Get-Item -Path .\).Name.ToLower() -replace '[^a-z0-9]', ''; if (-not $name) { $name = 'build' }; $name"`) do set CWD_NAME=%%i

set IMAGE_NAME=!CWD_NAME!_alpine
set CONTAINER_NAME=!CWD_NAME!_alpine_container

echo Building image !IMAGE_NAME!...
docker build -t !IMAGE_NAME! -f "%~dp0alpine.Dockerfile" "!SRC_DIR!"
set BUILD_ERR=!ERRORLEVEL!
if !BUILD_ERR! neq 0 goto :cleanup

echo Generating run script...
set "RUN_SCRIPT=!SRC_DIR!\.run_alpine_tests.sh"
(
echo set -e
echo export BUILD_TYPE="Debug"
echo echo "Setting up VCPKG..."
echo if [ ^^! -d "/vcpkg" ]; then
echo   git clone --branch project0 https://github.com/offscale/vcpkg.git /vcpkg
echo   /vcpkg/bootstrap-vcpkg.sh -disableMetrics
echo fi
echo export VCPKG_ROOT=/vcpkg
echo export VCPKG_INSTALLATION_ROOT=/vcpkg
echo export VCPKG_FORCE_SYSTEM_BINARIES=1
echo.
echo echo "======================================================================"
echo echo "Linux GCC | Shared Lib | Unicode | Multi-thread | LTO OFF | Vcpkg"
echo echo "======================================================================"
echo export CC=gcc
echo export CXX=g++
echo cmake -S /workspace_src -B /workspace_build/build_linux_gcc_shared -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" -DBUILD_SHARED_LIBS=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=UNICODE -DCDD_THREADING=ON -DCDD_DEPS=VCPKG -DC_CDD_BUILD_TESTING=ON -DC_ORM_BUILD_TESTING=ON -DC_ABSTRACT_HTTP_BUILD_TESTING=ON -DC_FS_BUILD_TESTING=ON -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF -DCMAKE_TOOLCHAIN_FILE=${VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake
echo cmake --build /workspace_build/build_linux_gcc_shared --config "${BUILD_TYPE}" --parallel 4
echo cd /workspace_build/build_linux_gcc_shared ^&^& ctest -C "${BUILD_TYPE}" --output-on-failure
echo cd /workspace_build
echo.
echo echo "======================================================================"
echo echo "Linux GCC | Static Lib | ANSI | Single-thread | LTO ON | FetchContent"
echo echo "======================================================================"
echo export CC=gcc
echo export CXX=g++
echo cmake -S /workspace_src -B /workspace_build/build_linux_gcc_static -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=ANSI -DCDD_THREADING=OFF -DCDD_DEPS=FETCHCONTENT -DC_CDD_BUILD_TESTING=ON -DC_ORM_BUILD_TESTING=ON -DC_ABSTRACT_HTTP_BUILD_TESTING=ON -DC_FS_BUILD_TESTING=ON -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF
echo cmake --build /workspace_build/build_linux_gcc_static --config "${BUILD_TYPE}" --parallel 4
echo cd /workspace_build/build_linux_gcc_static ^&^& ctest -C "${BUILD_TYPE}" --output-on-failure
echo cd /workspace_build
echo.
echo echo "======================================================================"
echo echo "Linux Clang | Static Lib | ANSI | Single-thread | LTO ON | System"
echo echo "======================================================================"
echo export CC=clang
echo export CXX=clang++
echo cmake -S /workspace_src -B /workspace_build/build_linux_clang_static -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=ANSI -DCDD_THREADING=OFF -DCDD_DEPS=SYSTEM -DC_CDD_BUILD_TESTING=ON -DC_ORM_BUILD_TESTING=ON -DC_ABSTRACT_HTTP_BUILD_TESTING=ON -DC_FS_BUILD_TESTING=ON -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF
echo cmake --build /workspace_build/build_linux_clang_static --config "${BUILD_TYPE}" --parallel 4
echo cd /workspace_build/build_linux_clang_static ^&^& ctest -C "${BUILD_TYPE}" --output-on-failure
echo cd /workspace_build
echo.
echo echo "======================================================================"
echo echo "Linux Clang | Shared Lib | Unicode | Multi-thread | LTO OFF | Vcpkg"
echo echo "======================================================================"
echo export CC=clang
echo export CXX=clang++
echo cmake -S /workspace_src -B /workspace_build/build_linux_clang_shared -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" -DBUILD_SHARED_LIBS=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=UNICODE -DCDD_THREADING=ON -DCDD_DEPS=VCPKG -DC_CDD_BUILD_TESTING=ON -DC_ORM_BUILD_TESTING=ON -DC_ABSTRACT_HTTP_BUILD_TESTING=ON -DC_FS_BUILD_TESTING=ON -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF -DCMAKE_TOOLCHAIN_FILE=${VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake
echo cmake --build /workspace_build/build_linux_clang_shared --config "${BUILD_TYPE}" --parallel 4
echo cd /workspace_build/build_linux_clang_shared ^&^& ctest -C "${BUILD_TYPE}" --output-on-failure
echo cd /workspace_build
) > "!RUN_SCRIPT!"

echo Running container !CONTAINER_NAME!...
docker run --name !CONTAINER_NAME! -v "%CD%:/workspace_build" -v "!SRC_DIR!:/workspace_src" !IMAGE_NAME! sh -c "tr -d '\r' < /workspace_src/.run_alpine_tests.sh | sh"
set RUN_ERR=!ERRORLEVEL!

:cleanup
echo Cleaning up container !CONTAINER_NAME! and image !IMAGE_NAME!...
docker rm -f !CONTAINER_NAME! 2>nul
docker rmi -f !IMAGE_NAME! 2>nul
if exist "!RUN_SCRIPT!" del /f "!RUN_SCRIPT!"

if !BUILD_ERR! neq 0 exit /b !BUILD_ERR!
if !RUN_ERR! neq 0 exit /b !RUN_ERR!
echo Alpine variations completed successfully.
exit /b 0
