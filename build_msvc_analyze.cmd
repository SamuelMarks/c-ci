@echo off
setlocal
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"

echo ======================================================================
echo Win MSVC 2022 ^| Static Analysis (/analyze)
echo ======================================================================
set "BUILD_DIR=%CD%\build_msvc_analyze"

cmake -S "%SRC_DIR%" -B "%BUILD_DIR%" -DCMAKE_C_FLAGS="/analyze" -DBUILD_SHARED_LIBS=OFF -DBUILD_TESTING=ON %*
if errorlevel 1 exit /b 1

cmake --build "%BUILD_DIR%" --config Debug
if errorlevel 1 exit /b 1

pushd "%BUILD_DIR%"
ctest -C Debug --output-on-failure
popd

echo Static analysis variation completed successfully.
