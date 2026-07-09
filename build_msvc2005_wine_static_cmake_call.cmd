@echo off
set "FETCH_ARGS="
set FETCH_ARGS=%FETCH_ARGS% -DFETCHCONTENT_SOURCE_DIR_PARSON="Z:\home\samuel\repos\c-ci\..\parson"
set FETCH_ARGS=%FETCH_ARGS% -DFETCHCONTENT_SOURCE_DIR_C-ABSTRACT-HTTP="Z:\home\samuel\repos\c-ci\..\c-abstract-http"
set FETCH_ARGS=%FETCH_ARGS% -DFETCHCONTENT_SOURCE_DIR_C89STRINGUTILS="Z:\home\samuel\repos\c-ci\..\c89stringutils"
set FETCH_ARGS=%FETCH_ARGS% -DFETCHCONTENT_SOURCE_DIR_CDD-C="Z:\home\samuel\repos\c-ci\..\cdd-c"
set FETCH_ARGS=%FETCH_ARGS% -DFETCHCONTENT_SOURCE_DIR_C-STR-SPAN="Z:\home\samuel\repos\c-ci\..\c-str-span"
set FETCH_ARGS=%FETCH_ARGS% -DFETCHCONTENT_SOURCE_DIR_C-ORM="Z:\home\samuel\repos\c-ci\..\c-orm"
cmake -S "Z:\home\samuel\repos\c-ci" -B "Z:\home\samuel\repos\c-ci\build_msvc2005_wine_static" -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Debug -DBUILD_SHARED_LIBS=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF -DBUILD_TESTING=ON -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebug %FETCH_ARGS% %*
