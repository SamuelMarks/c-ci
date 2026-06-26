call "%~dp0vcvarsalls_wine.cmd"
cd ../cdd-c/build_msvc2005_wine_static
set PATH=%CD%\Debug;%CD%\_deps\c89stringutils-build\Debug;%CD%\_deps\c_abstract_http-build\Debug;%PATH%
ctest -C Debug --output-on-failure
