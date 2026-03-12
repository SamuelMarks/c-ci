#!/bin/bash
set -e

SRC_DIR="$(pwd)"
BUILD_TYPE="Debug"

echo "======================================================================"
echo "macOS Clang | Shared Lib | Unicode | Multi-thread | LTO ON | FetchContent"
echo "======================================================================"
BUILD_DIR="${SRC_DIR}/build_macos_shared"
cmake -S "${SRC_DIR}" -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" \
  -DBUILD_SHARED_LIBS=ON \
  -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON \
  -DCDD_CHARSET=UNICODE \
  -DCDD_THREADING=ON \
  -DCDD_DEPS=FETCHCONTENT \
  -DC_CDD_BUILD_TESTING=ON -DC_ORM_BUILD_TESTING=ON -DC_ABSTRACT_HTTP_BUILD_TESTING=ON -DC_FS_BUILD_TESTING=ON -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF
cmake --build "${BUILD_DIR}" --config "${BUILD_TYPE}" --parallel 4
cd "${BUILD_DIR}" && ctest -C "${BUILD_TYPE}" --output-on-failure
cd "${SRC_DIR}"

echo "======================================================================"
echo "macOS Clang | Static Lib | ANSI | Single-thread | LTO OFF | System"
echo "======================================================================"
BUILD_DIR="${SRC_DIR}/build_macos_static"
cmake -S "${SRC_DIR}" -B "${BUILD_DIR}" -DCMAKE_BUILD_TYPE="${BUILD_TYPE}" \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF \
  -DCDD_CHARSET=ANSI \
  -DCDD_THREADING=OFF \
  -DCDD_DEPS=SYSTEM \
  -DC_CDD_BUILD_TESTING=ON -DC_ORM_BUILD_TESTING=ON -DC_ABSTRACT_HTTP_BUILD_TESTING=ON -DC_FS_BUILD_TESTING=ON -DBUILD_TESTING=ON -DCDD_MSVC_RTC=OFF
cmake --build "${BUILD_DIR}" --config "${BUILD_TYPE}" --parallel 4
cd "${BUILD_DIR}" && ctest -C "${BUILD_TYPE}" --output-on-failure
cd "${SRC_DIR}"

echo "macOS variations completed successfully."
