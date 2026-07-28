c-ci: Local CI scripts and GitHub Actions for building & testing C projects
===========================================================================

[![License: CC0-1.0](https://img.shields.io/badge/License-CC0_1.0-blue.svg)](http://creativecommons.org/publicdomain/zero/1.0/)

This repository hosts a robust, highly optimized, and shared GitHub Actions workflow designed exclusively for C projects in the CDD ecosystem (e.g., `c-orm`, `c-multiplatform`, `c-abstract-http`, `cdd-c`, and new projects).

By centralizing the CI pipeline here, all CDD projects automatically benefit from extensive, cross-platform build matrices without duplicating massive `.yml` configurations or wrangling complex environments.

## 🌍 Projects using c-ci

This is public for anyone to use. Here's where I use it:

| Name | Description | CI shield |
| :--- | :--- | :--- |
| [c-abstract-http](https://github.com/SamuelMarks/c-abstract-http) | HTTP/HTTPS client interface reusing abstractions for Windows (WinHTTP,WinINet), macOS (CommonCrypto), iOS, Android, GTK+4 (libsoup), with fallback to libcurl | [![CI](https://github.com/SamuelMarks/c-abstract-http/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/c-abstract-http/actions/workflows/ci.yml) |
| [c-fs](https://github.com/SamuelMarks/c-fs) | std::filesystem inspired interface for C89 (MSVC2005, Cygwin, MSVC2026, Linux, macOS, etc.) | [![CI](https://github.com/SamuelMarks/c-fs/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/c-fs/actions/workflows/ci.yml) |
| [c-multiplatform](https://github.com/SamuelMarks/c-multiplatform) | Cross platform GUI framework in ANSI C (C89), native for: Windows (GDI+); Linux (GTK+4); macOS (Cocoa); iOS; Android; web (WASM). Material 3. | [![CI](https://github.com/SamuelMarks/c-multiplatform/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/c-multiplatform/actions/workflows/ci.yml) |
| [c-orm](https://github.com/SamuelMarks/c-orm) | (PostgreSQL, SQLite, MySQL) ORM for C. Alembic/diesel style schema migration support. VERY portable. | [![CI](https://github.com/SamuelMarks/c-orm/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/c-orm/actions/workflows/ci.yml) |
| [c-rest-framework](https://github.com/SamuelMarks/c-rest-framework) | C REST Framework with builtin ORM (PostgreSQL, SQLite, MySQL) native on DOS, Cygwin, Windows, Linux, macOS, etc. | [![CI](https://github.com/SamuelMarks/c-rest-framework/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/c-rest-framework/actions/workflows/ci.yml) |
| [c-str-span](https://github.com/SamuelMarks/c-str-span) | UTF-8 replacement for C strings, supporting zero-copy use-cases (non-null-terminated). | [![CI](https://github.com/SamuelMarks/c-str-span/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/c-str-span/actions/workflows/ci.yml) |
| [c89stringutils](https://github.com/offscale/c89stringutils) | string functions from newer standards / common non-standards for C89 | [![CI](https://github.com/offscale/c89stringutils/actions/workflows/ci.yml/badge.svg)](https://github.com/offscale/c89stringutils/actions/workflows/ci.yml) |
| [cdd-c](https://github.com/SamuelMarks/cdd-c) | OpenAPI ↔ C. Frontend for C, concentrating on: generation from code; single-file analysis; modification; and emission (prettyprinting). | [![CI](https://github.com/SamuelMarks/cdd-c/actions/workflows/ci.yml/badge.svg)](https://github.com/SamuelMarks/cdd-c/actions/workflows/ci.yml) |

## 🌟 Key Features

*   **Sparse Matrix Optimization:** Exhaustive testing without exhaustive costs. We test combinations of every variable across 13 unique, carefully crafted profiles instead of 100+ raw permutations.
*   **Comprehensive Cross-Platform Support:**
    *   **Windows:** MSVC 2026 (Latest), MSVC 2022, MinGW, Cygwin *(MSVC 2005 support requires a self-hosted runner and is configured but disabled by default)*.
    *   **Linux:** Ubuntu with GCC and Clang. *Alpine Linux (musl) is supported via local Docker scripts.*
    *   **macOS:** Apple Clang.
    *   **Legacy Systems:** DOS via OpenWatcom *(local build script only)*.
*   **Valgrind Memory Checking:** Automatically run `ctest -T memcheck` with valgrind on Linux runners.
*   **Custom Package Management:** Easily install extra dependencies per-platform using native package managers (`extra_apt_packages`, `extra_brew_packages`, `extra_winget_packages`, `extra_cygwin_packages`).
*   **Target Linking:** Shared (`/MD`, `/MDd`) vs Static (`/MT`, `/MTd`) CRT linkage; Shared Library (`.dll`, `.so`, `.dylib`) vs Static Library (`.lib`, `.a`) output.
*   **Build Modifiers:** Link-Time Optimization (LTO) on/off, Charset variations (`UNICODE` vs `ANSI`), MSVC Runtime Checks (`RTC1`, `RTCu`, `RTCs`), and Threading limits.
*   **Cross-Platform Line Ending Safety:** Transparently converts source code using `unix2dos` and `dos2unix` depending on the compiler environment, preventing insidious compilation failures or macro breakage on MSVC vs GCC due to `\r\n` and `\n` discrepancies.
*   **Environment Isolation:** Disable CI environment inheritance with `disable_env_inheritance` or inject arbitrary variables securely using `env_vars`.

## 🛡️ Strict Error Percolation Tooling

In addition to CI orchestration, `c-ci` provides a robust, two-layered defense mechanism to eliminate a common source of undefined behavior in C: **silently discarded error returns**.

1.  **Layer 1 (Compiler Enforcement):**
    We provide a cross-platform header `include/c_error_percolation.h` that exports the `C_ERROR_NODISCARD` macro. By attaching this macro to your error `typedef` or `enum`, your compiler (GCC, Clang, MSVC) will immediately warn you (or fail via `-Werror`) if you forget to capture the result of an error-returning function (e.g., just writing `foo();`).

2.  **Layer 2 (AST CFG Analysis):**
    To ensure developers don't just capture the error to silence the compiler (e.g., `result_t rc = foo();` and then ignoring `rc`), we provide a dedicated Python pre-commit hook in `precommit_hooks/check_error_percolation_clang.py`. Powered by `libclang`, this hook parses the Abstract Syntax Tree (AST) to strictly enforce that the captured error is immediately checked in an `if` statement, not mutated, and correctly returned up the call stack (including `goto cleanup;` idioms).

For detailed usage, see the documentation in [`include/README.md`](include/README.md) and [`precommit_hooks/README.md`](precommit_hooks/README.md). You can also run the hook manually against your codebase to generate an LLM-friendly markdown report for automated auditing.

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
      # Optional: Change default build type here (default is Debug)
      build_type: 'Release'

      # Optional: Pass custom CMake configuration flags
      cmake_configure_flags: '-DBUILD_EXAMPLES=ON'

      # Optional: Pass custom CMake build flags
      cmake_build_flags: '--clean-first'

      # Optional: Override the project name used for the auto test flag (defaults to repo name)
      project_name: 'C_ORM'

      # Optional: Disable the automatic injection of -D<PROJECT_NAME>_BUILD_TESTING=ON
      auto_test_flag: true

      # Optional: Run ctest with valgrind (ctest -T memcheck) on Linux runners (default is true)
      run_valgrind: true

      # Optional: Install extra apt packages on Linux runners
      extra_apt_packages: 'libsqlite3-dev'

      # Optional: Install extra brew packages on macOS runners
      extra_brew_packages: 'sqlite'

      # Optional: Install extra winget packages on Windows runners
      extra_winget_packages: 'Ninja'

      # Optional: Install extra cygwin packages on Cygwin runners
      extra_cygwin_packages: 'libsqlite3-devel'

      # Optional: Disable environment variable inheritance for CMake/CTest
      disable_env_inheritance: true

      # Optional: Inject arbitrary environment variables into the job via JSON
      env_vars: ${{ toJson(env) }}

    env:
      # These will be automatically converted to JSON and injected via env_vars
      GIT_CONFIG_PARAMETERS: "'init.defaultBranch=main'"
      MY_CUSTOM_VAR: "Hello World"
```

---

## 💻 Local Build and Testing Scripts

In addition to the GitHub Actions workflow, this repository provides a suite of local build scripts. These scripts mirror the CI matrix locally and introduce supplementary targets that are tricky or expensive to run on standard GitHub-hosted runners.

### Duplicating CI Locally
You can run the major GitHub Actions variations directly on your Windows development machine:
*   **`duplicate_gh_actions.cmd`:** Runs the full suite sequentially, simulating the GitHub Actions matrix for MSVC (2026, 2022, 2005), MinGW, Cygwin, Ubuntu (via Docker), and Alpine (via Docker).
*   **`build_all_parallel.ps1`:** Runs the same builds in parallel using PowerShell jobs for drastically reduced local test times.
*   **`build_all.cmd` / `build_all_serial.cmd`:** Alternative entry points for sequential batch testing.

### Passing Extra Arguments to Local Scripts
All local build scripts now accept extra arguments that are passed directly to the underlying `cmake -S` configuration step.
*   **Windows (`.cmd`):** `build_msvc2026.cmd -DMY_CUSTOM_FLAG=ON`
*   **macOS/Linux (`.sh`):** `./build_macos.sh -DMY_CUSTOM_FLAG=ON`

### Individual Build Scripts
You can run specific environments directly if you are investigating a targeted issue:
*   `build_msvc2026.cmd` / `build_msvc2022.cmd` / `build_msvc2005.cmd`
*   `build_mingw.cmd` / `build_cygwin.cmd`
*   `build_docker_ubuntu.cmd` / `build_docker_alpine.cmd` *(Requires Docker)*
*   `build_dos_watcom.cmd` *(Requires OpenWatcom installed at `C:\usr\WATCOM`)*
*   `build_msvc_analyze.cmd` *(Runs MSVC Static Code Analysis)*
*   `build_macos.sh` *(Must be executed directly on a macOS host)*

---

## 📜 The CMake Contract

The magic of this reusable workflow lies in **cache variable injection**. For your CDD projects to function correctly in this matrix, your project's `CMakeLists.txt` must inspect and respond to several CDD-specific variables.

### Variables injected by the CI workflow

| CMake Variable | Possible Values | Description |
| :--- | :--- | :--- |
| `<PROJECT_NAME>_BUILD_TESTING`| `ON` | Automatically injected if `auto_test_flag` is true. The prefix is derived from the `project_name` input or the GitHub repository name (uppercased, hyphens replaced with underscores). |
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
GitHub no longer provides MSVC 2005 on hosted runners. The configuration for this legacy compiler currently sits in `.github/workflows/c-cmake-ci.yml`, but **is commented out by default**.
To enable it in the future:
1. Setup a self-hosted runner and assign it the label `msvc2005`.
2. Uncomment the MSVC 2005 section in the `matrix` block of `c-cmake-ci.yml`.

### End-of-line Conversions
Cygwin and MinGW tools often choke on `CRLF` endings if not configured exactly, while older MSVC tools can have unpredictable behavior with mixed `LF` line endings on multi-line macros. We explicitly use `unix2dos` right before CMake configuration for `msvc` environments, and `dos2unix` for `mingw`/`cygwin`/`gcc`/`clang`. If you encounter scripts failing during the build step, verify they are gracefully handling this conversion.
