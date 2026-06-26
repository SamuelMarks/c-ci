@echo off
setlocal EnableDelayedExpansion
set "SRC_DIR=%CD%\"
set "SRC_DIR=%SRC_DIR:~0,-1%"
set "BUILD_TYPE=Debug"

call "%~dp0vcvarsalls2026_wine.cmd"
if errorlevel 1 exit /b 1

:: NMake MSVC 2026 on Wine has a known U1038 lexer bug for files on the Z: drive.
:: We workaround this by copying the source and its siblings to the Wine C: drive.
for %%I in ("%SRC_DIR%") do set "REPO_NAME=%%~nxI"
set "WINE_C_SRC=C:\TempSrc_%REPO_NAME%"

echo Copying source to %WINE_C_SRC% to avoid Wine NMake Z: drive bug...
if exist "%WINE_C_SRC%" rmdir /s /q "%WINE_C_SRC%"
mkdir "%WINE_C_SRC%"
xcopy /E /I /Y /Q "%SRC_DIR%\*" "%WINE_C_SRC%\" >nul

for %%D in (parson c-abstract-http c89stringutils cdd-c c-str-span c-orm c-fs) do (
    if exist "%SRC_DIR%\..\%%D" (
        if exist "C:\TempSrc_%%D" rmdir /s /q "C:\TempSrc_%%D"
        mkdir "C:\TempSrc_%%D"
        xcopy /E /I /Y /Q "%SRC_DIR%\..\%%D\*" "C:\TempSrc_%%D\" >nul
    )
)

pushd "%WINE_C_SRC%"

echo ======================================================================
echo Win MSVC 2026 Wine ^| Shared Lib (MD) ^| Unicode ^| LTO OFF ^| FetchContent
echo ======================================================================
set "BUILD_DIR=%WINE_C_SRC%\build_msvc2026_wine_shared"

echo @echo off> "%BUILD_DIR%_cmake_call.cmd"
echo set "FETCH_ARGS=">> "%BUILD_DIR%_cmake_call.cmd"
if exist "C:\TempSrc_parson" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_PARSON="C:\TempSrc_parson">> "%BUILD_DIR%_cmake_call.cmd"
if exist "C:\TempSrc_c-abstract-http" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C_ABSTRACT_HTTP="C:\TempSrc_c-abstract-http">> "%BUILD_DIR%_cmake_call.cmd"
if exist "C:\TempSrc_c89stringutils" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C89STRINGUTILS="C:\TempSrc_c89stringutils">> "%BUILD_DIR%_cmake_call.cmd"
if exist "C:\TempSrc_cdd-c" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_CDD_C="C:\TempSrc_cdd-c">> "%BUILD_DIR%_cmake_call.cmd"
if exist "C:\TempSrc_c-str-span" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C_STR_SPAN="C:\TempSrc_c-str-span">> "%BUILD_DIR%_cmake_call.cmd"
if exist "C:\TempSrc_c-orm" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_C_ORM="C:\TempSrc_c-orm">> "%BUILD_DIR%_cmake_call.cmd"
if exist "C:\TempSrc_c-fs" echo set FETCH_ARGS=%%FETCH_ARGS%% -DFETCHCONTENT_SOURCE_DIR_CFS="C:\TempSrc_c-fs">> "%BUILD_DIR%_cmake_call.cmd"

echo cmake -S "%WINE_C_SRC%" -B "%BUILD_DIR%" -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=%BUILD_TYPE% -DBUILD_SHARED_LIBS=ON -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DCDD_CHARSET=UNICODE -DCDD_THREADING=ON -DCDD_DEPS=FETCHCONTENT -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL %%FETCH_ARGS%% %%*>> "%BUILD_DIR%_cmake_call.cmd"

call "%BUILD_DIR%_cmake_call.cmd" %*
if errorlevel 1 goto :fail
cmake --build "%BUILD_DIR%" --config "%BUILD_TYPE%"
if errorlevel 1 goto :fail

set "EXTRA_PATH="
if exist "%BUILD_DIR%\_deps" (
    for /d %%D in ("%BUILD_DIR%\_deps\*-build") do (
        set "EXTRA_PATH=!EXTRA_PATH!;%%D\%BUILD_TYPE%"
    )
)
set "PATH=%BUILD_DIR%\%BUILD_TYPE%!EXTRA_PATH!;%PATH%"

cd "%BUILD_DIR%"
ctest -C "%BUILD_TYPE%" --output-on-failure
if errorlevel 1 goto :fail

popd
echo Copying results back...
xcopy /E /I /Y /Q "%BUILD_DIR%" "%SRC_DIR%\build_msvc2026_wine_shared\" >nul

:: Cleanup
rmdir /s /q "%WINE_C_SRC%"
for %%D in (parson c-abstract-http c89stringutils cdd-c c-str-span c-orm c-fs) do (
    if exist "C:\TempSrc_%%D" rmdir /s /q "C:\TempSrc_%%D"
)

echo MSVC 2026 Wine variation completed successfully.
exit /b 0

:fail
popd
echo Build failed.
:: Cleanup on fail as well
rmdir /s /q "%WINE_C_SRC%"
for %%D in (parson c-abstract-http c89stringutils cdd-c c-str-span c-orm c-fs) do (
    if exist "C:\TempSrc_%%D" rmdir /s /q "C:\TempSrc_%%D"
)
exit /b 1
