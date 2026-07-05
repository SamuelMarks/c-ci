#!/bin/sh
set -e

SRC_DIR="$PWD"
BUILD_TYPE="Debug"

MSVC_WINE_PATH="${MSVC_WINE_PATH:-$HOME/my_msvc/opt/msvc}"
export PATH="${MSVC_WINE_PATH}/bin/x64:$PATH"

echo "Starting wineserver..."
wineserver -k || true
wineserver -p
wine wineboot

FETCH_ARGS=""
if [ -d "../parson" ]; then FETCH_ARGS="$FETCH_ARGS -DFETCHCONTENT_SOURCE_DIR_PARSON=\"${SRC_DIR}/../parson\""; fi
if [ -d "../c-abstract-http" ]; then FETCH_ARGS="$FETCH_ARGS -DFETCHCONTENT_SOURCE_DIR_C_ABSTRACT_HTTP=\"${SRC_DIR}/../c-abstract-http\""; fi
if [ -d "../c89stringutils" ]; then FETCH_ARGS="$FETCH_ARGS -DFETCHCONTENT_SOURCE_DIR_C89STRINGUTILS=\"${SRC_DIR}/../c89stringutils\""; fi
if [ -d "../cdd-c" ]; then FETCH_ARGS="$FETCH_ARGS -DFETCHCONTENT_SOURCE_DIR_CDD_C=\"${SRC_DIR}/../cdd-c\""; fi
if [ -d "../c-str-span" ]; then FETCH_ARGS="$FETCH_ARGS -DFETCHCONTENT_SOURCE_DIR_C_STR_SPAN=\"${SRC_DIR}/../c-str-span\""; fi
if [ -d "../c-orm" ]; then FETCH_ARGS="$FETCH_ARGS -DFETCHCONTENT_SOURCE_DIR_C_ORM=\"${SRC_DIR}/../c-orm\""; fi
if [ -d "../cfs" ]; then FETCH_ARGS="$FETCH_ARGS -DFETCHCONTENT_SOURCE_DIR_CFS=\"${SRC_DIR}/../cfs\""; fi


echo "======================================================================"
echo "MSVC-Wine | Shared Lib (MDd) | LTO OFF | Multi-thread | RTCs"
echo "======================================================================"
BUILD_DIR="${SRC_DIR}/build_msvc_wine_shared"
eval cmake -S "\"${SRC_DIR}\"" -B "\"${BUILD_DIR}\"" -DCMAKE_BUILD_TYPE="\"${BUILD_TYPE}\"" \
  -DCMAKE_SYSTEM_NAME=Windows \
  -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl \
  -DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=Embedded \
  -DCMAKE_CROSSCOMPILING_EMULATOR=wine \
  -DBUILD_SHARED_LIBS=ON \
  -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF \
  -DBUILD_TESTING=ON \
  -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebugDLL $FETCH_ARGS "$@"

cmake --build "${BUILD_DIR}" --config "${BUILD_TYPE}" --parallel 4

cd "${BUILD_DIR}"
EXTRA_WINEPATH=""
if [ -d "_deps" ]; then
    for dep in _deps/*-build; do
        if [ -d "$dep" ]; then
            EXTRA_WINEPATH="${EXTRA_WINEPATH};${BUILD_DIR}/${dep}"
        fi
    done
fi
export WINEPATH="${BUILD_DIR}${EXTRA_WINEPATH};${MSVC_WINE_PATH}/bin/x64;${MSVC_WINE_PATH}/VC/Redist/MSVC/14.51.36231/debug_nonredist/x64/Microsoft.VC145.DebugCRT;${MSVC_WINE_PATH}/Windows Kits/10/bin/10.0.26100.0/x64/ucrt"
ctest -C "${BUILD_TYPE}" --output-on-failure
cd "${SRC_DIR}"

echo "======================================================================"
echo "MSVC-Wine | Static Lib (MTd) | LTO ON | Single-thread | RTC1"
echo "======================================================================"
BUILD_DIR="${SRC_DIR}/build_msvc_wine_static"
eval cmake -S "\"${SRC_DIR}\"" -B "\"${BUILD_DIR}\"" -DCMAKE_BUILD_TYPE="\"${BUILD_TYPE}\"" \
  -DCMAKE_SYSTEM_NAME=Windows \
  -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl \
  -DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=Embedded \
  -DCMAKE_CROSSCOMPILING_EMULATOR=wine \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON \
  -DBUILD_TESTING=ON \
  -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebug $FETCH_ARGS "$@"

cmake --build "${BUILD_DIR}" --config "${BUILD_TYPE}" --parallel 4

cd "${BUILD_DIR}"
EXTRA_WINEPATH=""
if [ -d "_deps" ]; then
    for dep in _deps/*-build; do
        if [ -d "$dep" ]; then
            EXTRA_WINEPATH="${EXTRA_WINEPATH};${BUILD_DIR}/${dep}"
        fi
    done
fi
export WINEPATH="${BUILD_DIR}${EXTRA_WINEPATH};${MSVC_WINE_PATH}/bin/x64;${MSVC_WINE_PATH}/VC/Redist/MSVC/14.51.36231/debug_nonredist/x64/Microsoft.VC145.DebugCRT;${MSVC_WINE_PATH}/Windows Kits/10/bin/10.0.26100.0/x64/ucrt"
ctest -C "${BUILD_TYPE}" --output-on-failure
cd "${SRC_DIR}"

echo "All MSVC-Wine variations completed successfully."
