#!/bin/sh
set -e

SRC_DIR="$PWD"
BUILD_TYPE="Debug"

# MSVC 2005 path
export MSVC_2005_PATH="/media/samuel/OS1/Program Files (x86)/Microsoft Visual Studio 8"

if [ ! -d "$MSVC_2005_PATH" ]; then
    echo "MSVC 2005 not found at $MSVC_2005_PATH"
    exit 1
fi

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
if [ -d "../c-fs" ]; then FETCH_ARGS="$FETCH_ARGS -DFETCHCONTENT_SOURCE_DIR_CFS=\"${SRC_DIR}/../c-fs\""; fi

echo "======================================================================"
echo "MSVC 2005 Wine | Static Lib (MTd) | LTO OFF | Multi-thread | RTCs"
echo "======================================================================"
BUILD_DIR="${SRC_DIR}/build_msvc2005_wine_static"
mkdir -p "$BUILD_DIR"

# Create a sh wrapper for cl.exe to pass via wine
cat << 'WRAPPER' > "${BUILD_DIR}/cl_wrapper.sh"
#!/bin/sh
wine cmd /c "call Z:\\home\\samuel\\repos\\c-ci\\vcvarsalls_wine.cmd && cl.exe $@"
WRAPPER
chmod +x "${BUILD_DIR}/cl_wrapper.sh"

cat << 'WRAPPER' > "${BUILD_DIR}/link_wrapper.sh"
#!/bin/sh
wine cmd /c "call Z:\\home\\samuel\\repos\\c-ci\\vcvarsalls_wine.cmd && link.exe $@"
WRAPPER
chmod +x "${BUILD_DIR}/link_wrapper.sh"

cat << 'WRAPPER' > "${BUILD_DIR}/lib_wrapper.sh"
#!/bin/sh
wine cmd /c "call Z:\\home\\samuel\\repos\\c-ci\\vcvarsalls_wine.cmd && lib.exe $@"
WRAPPER
chmod +x "${BUILD_DIR}/lib_wrapper.sh"

cat << 'TOOLCHAIN' > "${BUILD_DIR}/msvc2005_toolchain.cmake"
set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_CROSSCOMPILING_EMULATOR "wine")
set(CMAKE_C_COMPILER "${CMAKE_BINARY_DIR}/cl_wrapper.sh")
set(CMAKE_CXX_COMPILER "${CMAKE_BINARY_DIR}/cl_wrapper.sh")
set(CMAKE_LINKER "${CMAKE_BINARY_DIR}/link_wrapper.sh")
set(CMAKE_AR "${CMAKE_BINARY_DIR}/lib_wrapper.sh")
TOOLCHAIN

eval cmake -S "\"${SRC_DIR}\"" -B "\"${BUILD_DIR}\"" -DCMAKE_TOOLCHAIN_FILE="\"${BUILD_DIR}/msvc2005_toolchain.cmake\"" -G Ninja -DCMAKE_BUILD_TYPE="\"${BUILD_TYPE}\"" \
  -DBUILD_SHARED_LIBS=OFF \
  -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=OFF \
  -DBUILD_TESTING=ON \
  -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDebug $FETCH_ARGS "$@"

cmake --build "${BUILD_DIR}" --config "${BUILD_TYPE}"

cd "${BUILD_DIR}"
EXTRA_WINEPATH=""
if [ -d "_deps" ]; then
    for dep in _deps/*-build; do
        if [ -d "$dep" ]; then
            EXTRA_WINEPATH="${EXTRA_WINEPATH};${BUILD_DIR}/${dep}"
        fi
    done
fi
export WINEPATH="${BUILD_DIR}${EXTRA_WINEPATH};Z:${MSVC_2005_PATH}/VC/bin;Z:${MSVC_2005_PATH}/Common7/IDE"
ctest -C "${BUILD_TYPE}" --output-on-failure
cd "${SRC_DIR}"

echo "MSVC 2005 Wine variation completed successfully."
