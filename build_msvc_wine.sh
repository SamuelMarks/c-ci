#!/bin/bash
set -e

SRC_DIR="$(pwd)"
BUILD_TYPE="Debug"

MSVC_WINE_PATH="${MSVC_WINE_PATH:-$HOME/my_msvc/opt/msvc}"
export PATH="${MSVC_WINE_PATH}/bin/x64:$PATH"

echo "Starting wineserver..."
wineserver -k || true
wineserver -p
wine wineboot

echo "======================================================================"
echo "MSVC-Wine | Shared Lib (MDd) | Unicode | LTO OFF | Multi-thread | FetchContent | RTCs"
echo "======================================================================"
BUILD_DIR="${SRC_DIR}/build_msvc_wine_shared"
cmake -S "${SRC_DIR}" -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" \
  -DCMAKE_SYSTEM_NAME=Windows \
  -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl \
  -DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=Embedded \
  -DCMAKE_CROSSCOMPILING_EMULATOR=wine \
  -DBUILD_SHARED_LIBS=ON \
  -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF \
  -DCDD_CHARSET=UNICODE \
  -DCDD_THREADING=ON \
  -DCDD_DEPS=FETCHCONTENT \
  -DBUILD_TESTING=ON -DCDD_MSVC_RTC=RTCs \
  -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebugDLL "$@"

cmake --build "${BUILD_DIR}" --config "${BUILD_TYPE}" --parallel 4

cd "${BUILD_DIR}"
export WINEPATH="${BUILD_DIR};${BUILD_DIR}/_deps/c89stringutils-build;${BUILD_DIR}/_deps/c_abstract_http-build;${MSVC_WINE_PATH}/bin/x64;${MSVC_WINE_PATH}/VC/Redist/MSVC/14.51.36231/debug_nonredist/x64/Microsoft.VC145.DebugCRT;${MSVC_WINE_PATH}/Windows Kits/10/bin/10.0.26100.0/x64/ucrt"
ctest -C "${BUILD_TYPE}" --output-on-failure
cd "${SRC_DIR}"

echo "======================================================================"
echo "MSVC-Wine | Static Lib (MTd) | ANSI | LTO ON | Single-thread | System | RTC1"
echo "======================================================================"
BUILD_DIR="${SRC_DIR}/build_msvc_wine_static"
cmake -S "${SRC_DIR}" -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" \
  -DCMAKE_SYSTEM_NAME=Windows \
  -DCMAKE_C_COMPILER=cl -DCMAKE_CXX_COMPILER=cl \
  -DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=Embedded \
  -DCMAKE_CROSSCOMPILING_EMULATOR=wine \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON \
  -DCDD_CHARSET=ANSI \
  -DCDD_THREADING=OFF \
  -DCDD_DEPS=SYSTEM \
  -DBUILD_TESTING=ON -DCDD_MSVC_RTC=RTC1 \
  -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebug "$@"

cmake --build "${BUILD_DIR}" --config "${BUILD_TYPE}" --parallel 4

cd "${BUILD_DIR}"
export WINEPATH="${BUILD_DIR};${BUILD_DIR}/_deps/c89stringutils-build;${BUILD_DIR}/_deps/c_abstract_http-build;${MSVC_WINE_PATH}/bin/x64;${MSVC_WINE_PATH}/VC/Redist/MSVC/14.51.36231/debug_nonredist/x64/Microsoft.VC145.DebugCRT;${MSVC_WINE_PATH}/Windows Kits/10/bin/10.0.26100.0/x64/ucrt"
ctest -C "${BUILD_TYPE}" --output-on-failure
cd "${SRC_DIR}"

echo "All MSVC-Wine variations completed successfully."
