Local CI scripts and GitHub Actions for building & testing C projects
=====================================================================

[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-blue.svg)](http://creativecommons.org/publicdomain/zero/1.0/)

This repository hosts a robust, highly optimized, and shared GitHub Actions workflow designed exclusively for C projects in the CDD ecosystem (e.g., `c-orm`, `c-multiplatform`, `c-abstract-http`, `cdd-c`, and new projects).

By centralizing the CI pipeline here, all CDD projects automatically benefit from extensive, cross-platform build matrices without duplicating massive `.yml` configurations or wrangling complex environments.

## 🌟 Key Features

*   **Sparse Matrix Optimization:** Exhaustive testing without exhaustive costs. We test combinations of every variable across 13 unique, carefully crafted profiles instead of 100+ raw permutations.
*   **Comprehensive Cross-Platform Support:**
    *   **Windows:** MSVC 2026 (Latest), MSVC 2022, MinGW, Cygwin *(MSVC 2005 support requires a self-hosted runner and is configured but disabled by default)*.
    *   **Linux:** Ubuntu with GCC and Clang.
    *   **macOS:** Apple Clang.
*   **Target Linking:** Shared (`/MD`, `/MDd`) vs Static (`/MT`, `/MTd`) CRT linkage; Shared Library (`.dll`, `.so`, `.dylib`) vs Static Library (`.lib`, `.a`) output.
*   **Build Modifiers:** Link-Time Optimization (LTO) on/off, Charset variations (`UNICODE` vs `ANSI`), MSVC Runtime Checks (`RTC1`, `RTCu`, `RTCs`), and Threading limits.
*   **Cross-Platform Line Ending Safety:** Transparently converts source code using `unix2dos` and `dos2unix` depending on the compiler environment, preventing insidious compilation failures or macro breakage on MSVC vs GCC due to `\r\n` and `\n` discrepancies.

---

## 🚀 How to Use in Your Project

Can I just push this up and start using it? **Yes!** Once this repository (`c-ci`) is pushed publicly to GitHub, any repository (public or private) can invoke it. There is nothing "fancy" you have to configure in GitHub's settings as long as standard GitHub-hosted runners are enabled.

Create `.github/workflows/ci.yml` in your target repository (e.g., `c-orm`) with the following code:

```yaml
name: CI

on:
  push:
    branches: [ "main", "master" ]
  pull_request:
    branches: [ "main", "master" ]

jobs:
  build:
    uses: SamuelMarks/c-ci/.github/workflows/c-cmake-ci.yml@master
    with:
      # Optional: Change default build type here
      build_type: 'Release'
```

---

## 📜 The CMake Contract

The magic of this reusable workflow lies in **cache variable injection**. For your CDD projects to function correctly in this matrix, your project's `CMakeLists.txt` must inspect and respond to several CDD-specific variables.

### Variables injected by the CI workflow

| CMake Variable | Possible Values | Description |
| :--- | :--- | :--- |
| `BUILD_SHARED_LIBS` | `ON`, `OFF` | Native CMake variable. Determines if `add_library` produces shared or static libraries. |
| `CMAKE_INTERPROCEDURAL_OPTIMIZATION`| `ON`, `OFF` | Native CMake variable for Link-Time Optimization (LTO). |
| `CMAKE_MSVC_RUNTIME_LIBRARY` | `MultiThreaded...`| Native CMake variable. Toggles `/MT`, `/MD`, `/MTd`, `/MDd`. |
| `CDD_CHARSET` | `UNICODE`, `ANSI` | Used for defining string widths (especially on Windows). |
| `CDD_THREADING` | `ON`, `OFF` | Instructs the project on whether to link threading primitives (e.g., pthreads). |
| `CDD_DEPS` | `SYSTEM`, `VCPKG`, `FETCHCONTENT`| The method your `CMakeLists.txt` should use to resolve its dependencies. |
| `CDD_MSVC_RTC` | `RTC1`, `RTCs`, `RTCu`, `OFF` | Used to conditionally inject Runtime Checks in MSVC debug modes. |

### Minimal Example `CMakeLists.txt` Snippet

Ensure the following logic (or similar) exists in your projects so they actually execute the test variations properly:

```cmake
# 1. Handle Charset (Crucial for Windows API)
if(CDD_CHARSET STREQUAL "UNICODE")
    add_compile_definitions(UNICODE _UNICODE)
endif()

# 2. Dependency Resolution Strategy
if(CDD_DEPS STREQUAL "VCPKG")
    # GitHub Action automatically injects the vcpkg toolchain path for you.
    find_package(ZLIB REQUIRED)
elseif(CDD_DEPS STREQUAL "SYSTEM")
    find_package(ZLIB REQUIRED)
elseif(CDD_DEPS STREQUAL "FETCHCONTENT")
    include(FetchContent)
    FetchContent_Declare(
        zlib
        GIT_REPOSITORY https://github.com/madler/zlib.git
        GIT_TAG        v1.3
    )
    FetchContent_MakeAvailable(zlib)
endif()

# 3. Handle MSVC Runtime Error Checks
if(MSVC AND NOT CDD_MSVC_RTC STREQUAL "OFF")
    add_compile_options("/${CDD_MSVC_RTC}")
endif()

# 4. Handle Threading
if(CDD_THREADING STREQUAL "ON")
    set(THREADS_PREFER_PTHREAD_FLAG ON)
    find_package(Threads REQUIRED)
    link_libraries(Threads::Threads)
endif()
```

---

## 🛠 Advanced Information & Troubleshooting

### Dependency Resolution (vcpkg)
When the matrix runs a profile utilizing `VCPKG`, it automatically passes `-DCMAKE_TOOLCHAIN_FILE` pointing to the pre-installed vcpkg location found on standard GitHub-hosted runners (`$VCPKG_INSTALLATION_ROOT`). You do not need to build `vcpkg` yourself.

### Self-Hosted Runners (MSVC 2005)
GitHub no longer provides MSVC 2005 on hosted runners. The configuration for this legacy compiler currently sits in `.github/workflows/cdd-cmake-ci.yml`, but **is commented out by default**.
To enable it in the future:
1. Setup a self-hosted runner and assign it the label `msvc2005`.
2. Uncomment the MSVC 2005 section in the `matrix` block of `cdd-cmake-ci.yml`.

### End-of-line Conversions
Cygwin and MinGW tools often choke on `CRLF` endings if not configured exactly, while older MSVC tools can have unpredictable behavior with mixed `LF` line endings on multi-line macros. We explicitly use `unix2dos` right before CMake configuration for `msvc` environments, and `dos2unix` for `mingw`/`cygwin`/`gcc`/`clang`. If you encounter scripts failing during the build step, verify they are gracefully handling this conversion.
