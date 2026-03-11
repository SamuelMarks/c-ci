@echo off
echo Running all builds in serial...
call "%~dp0build_msvc2005.cmd"
call "%~dp0build_msvc2022.cmd"
call "%~dp0build_msvc2026.cmd"
call "%~dp0build_mingw.cmd"
call "%~dp0build_cygwin.cmd"
call "%~dp0build_docker_ubuntu.cmd"
call "%~dp0build_docker_alpine.cmd"
echo All serial builds completed.
