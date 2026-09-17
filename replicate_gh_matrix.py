#!/usr/bin/env python3
"""
Replicate GitHub Actions matrix runs locally.

This script parses a GitHub Actions workflow YAML file to extract the matrix of jobs,
and allows running specific MSVC, Apple Clang, Linux GCC/Clang, MinGW, Cygwin, or
WebAssembly Emscripten jobs locally to replicate CI behavior without needing to push to GitHub.

It handles cross-platform execution intelligently:
- Runs macOS jobs natively on macOS.
- Runs MSVC jobs natively on Windows, or via WINE on Unix-like systems.
- Runs Linux jobs natively on Linux (with automatic clang/gcc fallbacks),
  via Docker on non-Linux systems, or via WSL (Windows Subsystem for Linux) on Windows.
- Runs WebAssembly (Emscripten) jobs via Docker using emscripten/emsdk.
- Runs MinGW cross-compilation jobs via Docker or native tools.
- Supports standalone workflow jobs like memory-check (ASAN / Valgrind).
"""

import os
import sys
import yaml
import shutil
import argparse
import subprocess
from typing import List, Dict, Any


def load_matrix(yaml_path: str) -> List[Dict[str, Any]]:
    """
    Load the GitHub Actions workflow YAML and extract matrix jobs.

    If yaml_path is a calling workflow (e.g., ci.yml) that invokes c-cmake-ci.yml,
    it resolves c-cmake-ci.yml and adds both the reusable matrix jobs and any
    standalone jobs (like memory-check).

    Args:
        yaml_path (str): The file path to the GitHub Actions workflow YAML file.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing jobs to run.
    """
    with open(yaml_path, "r") as f:
        workflow = yaml.safe_load(f)

    jobs_dict = workflow.get("jobs", {})
    supported_jobs: List[Dict[str, Any]] = []

    # Check if yaml_path is directly c-cmake-ci.yml
    if "build-and-test" in jobs_dict:
        matrix_includes = (
            jobs_dict["build-and-test"]
            .get("strategy", {})
            .get("matrix", {})
            .get("include", [])
        )
        supported_jobs.extend(matrix_includes)
        extra_cmake_flags = ""
        for job_id, job_data in jobs_dict.items():
            if isinstance(job_data, dict) and "with" in job_data:
                extra_cmake_flags = job_data["with"].get("cmake_configure_flags", "")
                if extra_cmake_flags:
                    break
        if extra_cmake_flags:
            for job in supported_jobs:
                job["cmake_configure_flags"] = extra_cmake_flags
        return supported_jobs

    # Otherwise, it might be a caller workflow (e.g., .github/workflows/ci.yml)
    # Check for references to c-cmake-ci.yml
    shared_ci_candidates = [
        os.path.join(
            os.path.dirname(__file__), ".github", "workflows", "c-cmake-ci.yml"
        ),
        os.path.expanduser("~/repos/c-ci/.github/workflows/c-cmake-ci.yml"),
    ]
    shared_ci_path = None
    for cand in shared_ci_candidates:
        if os.path.exists(cand):
            shared_ci_path = cand
            break

    if shared_ci_path:
        with open(shared_ci_path, "r") as f:
            shared_wf = yaml.safe_load(f)
        matrix_includes = (
            shared_wf.get("jobs", {})
            .get("build-and-test", {})
            .get("strategy", {})
            .get("matrix", {})
            .get("include", [])
        )
        supported_jobs.extend(matrix_includes)

    # Also detect standalone jobs like memory-check
    for job_id, job_data in jobs_dict.items():
        if job_id == "build":
            continue
        if job_id == "memory-check":
            supported_jobs.append(
                {
                    "name": "memory-check (ASAN & Valgrind)",
                    "type": "memory-check",
                    "os": "ubuntu-latest",
                    "compiler": "gcc",
                }
            )
        elif isinstance(job_data, dict) and "steps" in job_data:
            supported_jobs.append(
                {
                    "name": f"standalone job: {job_id}",
                    "type": "standalone",
                    "job_id": job_id,
                    "os": job_data.get("runs-on", "ubuntu-latest"),
                }
            )

    extra_cmake_flags = ""
    for job_id, job_data in jobs_dict.items():
        if isinstance(job_data, dict) and "with" in job_data:
            extra_cmake_flags = job_data["with"].get("cmake_configure_flags", "")
            if extra_cmake_flags:
                break
    if extra_cmake_flags:
        for job in supported_jobs:
            job["cmake_configure_flags"] = extra_cmake_flags
    return supported_jobs


def print_jobs(jobs: List[Dict[str, Any]]) -> None:
    """Print the list of available jobs to the console.

    Args:
        jobs (List[Dict[str, Any]]): A list of dictionaries containing job configurations.
    """
    print(
        "Available Matrix Jobs (MSVC, AppleClang, Linux GCC/Clang, MinGW, Cygwin, WebAssembly):"
    )
    print("-" * 70)
    for i, job in enumerate(jobs):
        print(f"[{i}] {job.get('name')}")
    print("-" * 70)


def _run_emscripten_in_docker(job: Dict[str, Any], source_dir: str) -> None:
    """Run a WebAssembly / Emscripten job inside an emscripten/emsdk Docker container.

    Args:
        job (Dict[str, Any]): Dictionary containing job configurations.
        source_dir (str): Path to the source directory to build.
    """
    print(f"Replicating Job in Docker (Emscripten): {job.get('name')}")
    if not shutil.which("docker"):
        print("Error: 'docker' is required but not found in PATH.")
        sys.exit(1)

    docker_check = subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if docker_check.returncode != 0:
        print("Docker daemon not running; skipping")
        return

    build_type = "Debug"
    shared = str(job.get("shared", "OFF"))
    lto = str(job.get("lto", "OFF"))
    charset = str(job.get("charset", "ANSI"))
    thread = str(job.get("thread", "ON"))
    deps = str(job.get("deps", "FETCHCONTENT"))

    build_dir_name = "build_wasm_docker"
    container_src = "/workspace"
    container_build = f"/workspace/{build_dir_name}"
    proj_name = os.path.basename(os.path.abspath(source_dir)).replace("-", "_").upper()

    cmake_args = [
        "emcmake",
        "cmake",
        "-S",
        container_src,
        "-B",
        container_build,
        f"-DCMAKE_BUILD_TYPE={build_type}",
        f"-DBUILD_SHARED_LIBS={shared}",
        f"-DCMAKE_INTERPROCEDURAL_OPTIMIZATION={lto}",
        f"-DCDD_CHARSET={charset}",
        f"-DCDD_THREADING={thread}",
        f"-DCDD_DEPS={deps}",
        "-DBUILD_TESTING=ON",
        f"-D{proj_name}_BUILD_TESTING=ON",
    ]
    if job.get("cmake_configure_flags"):
        import shlex

        cmake_args.extend(shlex.split(job["cmake_configure_flags"]))

    extra_mounts = []
    user_vcpkg = os.path.expanduser("~/repos/vcpkg")
    if deps == "VCPKG":
        setup_steps.append(
            "if ! which autoconf >/dev/null 2>&1; then apt-get update -yqq && apt-get install -yqq autoconf automake libtool; fi"
        )
        if os.path.exists(
            os.path.join(user_vcpkg, "scripts", "buildsystems", "vcpkg.cmake")
        ):
            extra_mounts.extend(["-v", f"{user_vcpkg}:/vcpkg"])
            cmake_args.append(
                "-DCMAKE_TOOLCHAIN_FILE=/vcpkg/scripts/buildsystems/vcpkg.cmake"
            )
        else:
            cmake_args.append(
                "-DCMAKE_TOOLCHAIN_FILE=/workspace/vcpkg/scripts/buildsystems/vcpkg.cmake"
            )

    cmd_str = (
        " ".join(cmake_args)
        + f" && cmake --build {container_build} --config {build_type}"
        + f" && cd {container_build} && ctest -C {build_type} --output-on-failure"
    )

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{os.path.abspath(source_dir)}:{container_src}",
        "-w",
        container_src,
        "emscripten/emsdk:latest",
        "sh",
        "-c",
        cmd_str,
    ]

    print(f"\n> Executing Docker command:\n{' '.join(docker_cmd)}")
    res = subprocess.run(docker_cmd)
    if res.returncode != 0:
        print("\nEmscripten Docker execution failed!")
        sys.exit(res.returncode)
    else:
        print("\nAll tests passed successfully in Docker (Emscripten)!")


def _run_linux_in_docker(
    job: Dict[str, Any], source_dir: str, run_valgrind: bool = True
) -> None:
    """Run a Linux CI job inside a Docker container.

    Args:
        job (Dict[str, Any]): Dictionary containing job configurations.
        source_dir (str): Path to the source directory to build.
        run_valgrind (bool): Whether to execute Valgrind memory tests. Defaults to True.
    """
    print(f"Replicating Job in Docker: {job.get('name')}")
    if not shutil.which("docker"):
        print("Error: 'docker' is required but not found in PATH.")
        sys.exit(1)

    docker_check = subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if docker_check.returncode != 0:
        print("Docker socket not running; skipping")
        return

    build_type = "Debug"
    shared = str(job.get("shared", "OFF"))
    lto = str(job.get("lto", "OFF"))
    charset = str(job.get("charset", "UNICODE"))
    thread = str(job.get("thread", "ON"))
    deps = str(job.get("deps", "FETCHCONTENT"))
    compiler = str(job.get("compiler", "gcc"))

    job_slug = (
        f"{compiler}_{job.get('shared', 'off')}_{job.get('deps', 'fetch')}".lower()
    )
    build_dir_name = f"build_docker_{job_slug}"
    container_src = "/workspace"
    container_build = f"/workspace/{build_dir_name}"

    proj_name = os.path.basename(os.path.abspath(source_dir)).replace("-", "_").upper()
    cc = compiler
    cxx = "clang++" if cc == "clang" else "g++"

    cmake_args = [
        "cmake",
        "-S",
        container_src,
        "-B",
        container_build,
        f"-DCMAKE_BUILD_TYPE={build_type}",
        f"-DBUILD_SHARED_LIBS={shared}",
        f"-DCMAKE_INTERPROCEDURAL_OPTIMIZATION={lto}",
        f"-DCDD_CHARSET={charset}",
        f"-DCDD_THREADING={thread}",
        f"-DCDD_DEPS={deps}",
        "-DBUILD_TESTING=ON",
        f"-D{proj_name}_BUILD_TESTING=ON",
        f"-DCMAKE_C_COMPILER={cc}",
        f"-DCMAKE_CXX_COMPILER={cxx}",
    ]

    os_name = str(job.get("os", ""))
    is_alpine = os_name.startswith("alpine")

    img_check = subprocess.run(
        ["docker", "image", "inspect", "c-ci-ubuntu:latest"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    has_local_image = (img_check.returncode == 0) and not is_alpine

    setup_steps = []
    if is_alpine:
        image = "alpine:latest"
        setup_steps.append(
            "apk add --no-cache cmake build-base clang dos2unix sqlite-dev valgrind linux-headers bash git curl zip unzip tar pkgconfig"
        )
    elif has_local_image:
        image = "c-ci-ubuntu:latest"
    else:
        image = "ubuntu:24.04"
        setup_steps.append(
            "apt-get update -yqq && apt-get install -yqq build-essential cmake clang gcc g++ dos2unix libsqlite3-dev git curl zip unzip tar pkg-config valgrind"
        )

    extra_mounts = []
    user_vcpkg = os.path.expanduser("~/repos/vcpkg")
    if deps == "VCPKG":
        setup_steps.append(
            "if ! which autoconf >/dev/null 2>&1; then apt-get update -yqq && apt-get install -yqq autoconf automake libtool; fi"
        )
        if os.path.exists(
            os.path.join(user_vcpkg, "scripts", "buildsystems", "vcpkg.cmake")
        ):
            extra_mounts.extend(["-v", f"{user_vcpkg}:/vcpkg"])
            cmake_args.append(
                "-DCMAKE_TOOLCHAIN_FILE=/vcpkg/scripts/buildsystems/vcpkg.cmake"
            )
        else:
            setup_steps.append(
                "if [ ! -d /workspace/vcpkg ]; then "
                "git clone https://github.com/offscale/vcpkg.git -b project0 /workspace/vcpkg && "
                "/workspace/vcpkg/bootstrap-vcpkg.sh; "
                "fi"
            )
            cmake_args.append(
                "-DCMAKE_TOOLCHAIN_FILE=/workspace/vcpkg/scripts/buildsystems/vcpkg.cmake"
            )

    build_cmd = f"cmake --build {container_build} --config {build_type} --parallel 4"
    test_cmd = f"cd {container_build} && ctest -C {build_type} --output-on-failure"

    all_commands = setup_steps + [" ".join(cmake_args), build_cmd, test_cmd]

    if run_valgrind:
        valgrind_cmd = f"cd {container_build} && ctest -T memcheck --output-on-failure"
        all_commands.append(valgrind_cmd)

    cmd_str = " && ".join(all_commands)

    docker_cmd = (
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{os.path.abspath(source_dir)}:{container_src}",
        ]
        + extra_mounts
        + [
            "-w",
            container_src,
            image,
            "sh",
            "-c",
            cmd_str,
        ]
    )

    print(f"\n> Executing Docker command:\n{' '.join(docker_cmd)}")
    res = subprocess.run(docker_cmd)
    if res.returncode != 0:
        print("\nDocker execution failed!")
        sys.exit(res.returncode)
    else:
        print("\nAll tests passed successfully in Docker!")


def _run_memory_check_in_docker(job: Dict[str, Any], source_dir: str) -> None:
    """Run memory-check (ASAN & Valgrind) inside Docker.

    Args:
        job (Dict[str, Any]): Dictionary containing job configurations.
        source_dir (str): Path to the source directory to build.
    """
    print(f"Replicating Memory-Check (ASAN & Valgrind) in Docker")
    if not shutil.which("docker"):
        print("Error: 'docker' is required but not found in PATH.")
        sys.exit(1)

    docker_check = subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    if docker_check.returncode != 0:
        print("Docker socket not running; skipping")
        return

    container_src = "/workspace"
    img_check = subprocess.run(
        ["docker", "image", "inspect", "c-ci-ubuntu:latest"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    image = "c-ci-ubuntu:latest" if img_check.returncode == 0 else "ubuntu:24.04"
    pkg_cmd = (
        ""
        if img_check.returncode == 0
        else "apt-get update -yqq && apt-get install -yqq build-essential cmake clang gcc g++ dos2unix libsqlite3-dev git valgrind && "
    )
    extra_mounts = []

    cmd_str = (
        f"{pkg_cmd}"
        "rm -rf /workspace/build_asan_docker && "
        "cmake -S /workspace -B /workspace/build_asan_docker -DCMAKE_BUILD_TYPE=Debug -DCDD_DEPS=FETCHCONTENT -DC_CDD_USE_ASAN=ON -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++ && "
        "cmake --build /workspace/build_asan_docker --parallel 4 && "
        "cd /workspace/build_asan_docker && ctest --output-on-failure"
    )

    extra_mounts = []
    docker_cmd = (
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{os.path.abspath(source_dir)}:{container_src}",
        ]
        + extra_mounts
        + [
            "-w",
            container_src,
            image,
            "sh",
            "-c",
            cmd_str,
        ]
    )

    print(f"\n> Executing Docker command:\n{' '.join(docker_cmd)}")
    res = subprocess.run(docker_cmd)
    if res.returncode != 0:
        print("\nMemory-check (ASAN) failed!")
        sys.exit(res.returncode)
    else:
        print("\nMemory-check passed successfully!")


def _run_mingw_in_docker(job: Dict[str, Any], source_dir: str) -> None:
    """Run MinGW cross-compilation inside Docker with x86_64-w64-mingw32-gcc and wine.

    Args:
        job (Dict[str, Any]): Dictionary containing job configurations.
        source_dir (str): Path to the source directory to build.
    """
    print(f"Replicating MinGW Job in Docker: {job.get('name')}")
    if not shutil.which("docker"):
        print("Error: 'docker' is required but not found in PATH.")
        sys.exit(1)

    build_type = "Debug"
    shared = str(job.get("shared", "OFF"))
    lto = str(job.get("lto", "OFF"))
    charset = str(job.get("charset", "UNICODE"))
    thread = str(job.get("thread", "ON"))
    deps = str(job.get("deps", "FETCHCONTENT"))

    build_dir_name = "build_docker_mingw"
    container_src = "/workspace"
    container_build = f"/workspace/{build_dir_name}"
    proj_name = os.path.basename(os.path.abspath(source_dir)).replace("-", "_").upper()

    img_check = subprocess.run(
        ["docker", "image", "inspect", "c-ci-ubuntu:latest"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    image = "c-ci-ubuntu:latest" if img_check.returncode == 0 else "ubuntu:24.04"

    pkg_cmd = (
        ""
        if img_check.returncode == 0
        else "apt-get update -yqq && apt-get install -yqq gcc-mingw-w64-x86-64 g++-mingw-w64-x86-64 wine wine64 && "
    )
    extra_mounts = []
    user_vcpkg = os.path.expanduser("~/repos/vcpkg")
    if deps == "VCPKG":
        if os.path.exists(
            os.path.join(user_vcpkg, "scripts", "buildsystems", "vcpkg.cmake")
        ):
            extra_mounts.extend(["-v", f"{user_vcpkg}:/vcpkg"])

    cmake_args = [
        "cmake",
        "-S",
        container_src,
        "-B",
        container_build,
        f"-DCMAKE_BUILD_TYPE={build_type}",
        f"-DBUILD_SHARED_LIBS={shared}",
        f"-DCMAKE_INTERPROCEDURAL_OPTIMIZATION={lto}",
        f"-DCDD_CHARSET={charset}",
        f"-DCDD_THREADING={thread}",
        f"-DCDD_DEPS={deps}",
        "-DBUILD_TESTING=ON",
        f"-D{proj_name}_BUILD_TESTING=ON",
        "-DCMAKE_SYSTEM_NAME=Windows",
        "-DCMAKE_SYSTEM_PROCESSOR=x86_64",
        "-DTARGET_ARCH=AMD64",
        "-DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc",
        "-DCMAKE_CXX_COMPILER=x86_64-w64-mingw32-g++",
        "-DCMAKE_CROSSCOMPILING_EMULATOR=wine",
    ]

    build_cmd = f"cmake --build {container_build} --config {build_type} --parallel 4"
    test_cmd = f"cd {container_build} && ctest -C {build_type} --output-on-failure"

    cmd_str = f"{pkg_cmd}{' '.join(cmake_args)} && {build_cmd} && {test_cmd}"

    docker_cmd = (
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{os.path.abspath(source_dir)}:{container_src}",
        ]
        + extra_mounts
        + [
            "-w",
            container_src,
            image,
            "sh",
            "-c",
            cmd_str,
        ]
    )

    print(f"\n> Executing Docker command:\n{' '.join(docker_cmd)}")
    res = subprocess.run(docker_cmd)
    if res.returncode != 0:
        print("\nMinGW Docker execution failed!")
        sys.exit(res.returncode)
    else:
        print("\nMinGW tests passed successfully in Docker!")


def _run_linux_in_wsl(job: Dict[str, Any], source_dir: str) -> None:
    """Run a Linux CI job using Windows Subsystem for Linux (WSL).

    Args:
        job (Dict[str, Any]): Dictionary containing job configurations.
        source_dir (str): Path to the source directory to build.
    """
    print(f"Replicating Job in WSL: {job.get('name')}")
    if not shutil.which("wsl"):
        print("Error: 'wsl' is required but not found in PATH.")
        sys.exit(1)

    build_type = "Debug"
    shared = str(job.get("shared", "OFF"))
    lto = str(job.get("lto", "OFF"))
    charset = str(job.get("charset", "UNICODE"))
    thread = str(job.get("thread", "ON"))
    deps = str(job.get("deps", "FETCHCONTENT"))
    compiler = str(job.get("compiler", "gcc"))

    job_slug = (
        f"{compiler}_{job.get('shared', 'off')}_{job.get('deps', 'fetch')}".lower()
    )
    build_dir_name = f"build_wsl_{job_slug}"

    proj_name = os.path.basename(os.path.abspath(source_dir)).replace("-", "_").upper()
    cc = compiler
    cxx = "clang++" if cc == "clang" else "g++"

    cmake_args = [
        "cmake",
        "-S",
        ".",
        "-B",
        build_dir_name,
        f"-DCMAKE_BUILD_TYPE={build_type}",
        f"-DBUILD_SHARED_LIBS={shared}",
        f"-DCMAKE_INTERPROCEDURAL_OPTIMIZATION={lto}",
        f"-DCDD_CHARSET={charset}",
        f"-DCDD_THREADING={thread}",
        f"-DCDD_DEPS={deps}",
        "-DBUILD_TESTING=ON",
        f"-D{proj_name}_BUILD_TESTING=ON",
        f"-DCMAKE_C_COMPILER={cc}",
        f"-DCMAKE_CXX_COMPILER={cxx}",
    ]

    build_args = [
        "cmake",
        "--build",
        build_dir_name,
        "--config",
        build_type,
        "--parallel",
        "1" if (is_msvc and host_os != "win32") else "4",
    ]
    if is_msvc and host_os != "win32":
        build_args.append("--verbose")
    ctest_args = ["ctest", "-C", build_type, "--output-on-failure"]

    cmd_str = (
        " ".join(cmake_args)
        + " && "
        + " ".join(build_args)
        + " && "
        + f"cd {build_dir_name} && "
        + " ".join(ctest_args)
    )

    wsl_cmd = ["wsl", "--exec", "bash", "-c", cmd_str]

    print(f"\n> Executing WSL command:\n{' '.join(wsl_cmd)}")
    res = subprocess.run(wsl_cmd, cwd=source_dir)
    if res.returncode != 0:
        print("\nWSL execution failed!")
        sys.exit(res.returncode)
    else:
        print("\nAll tests passed successfully in WSL!")


def run_job(
    job: Dict[str, Any],
    source_dir: str,
    use_wsl: bool = False,
    run_valgrind: bool = True,
) -> None:
    """Run a specific job locally by constructing and executing CMake commands.

    Args:
        job (Dict[str, Any]): Dictionary containing job configurations.
        source_dir (str): Path to the source directory to build.
        use_wsl (bool): Whether to run Linux jobs under WSL. Defaults to False.
        run_valgrind (bool): Whether to execute Valgrind memory checks. Defaults to True.
    """
    if job.get("type") == "memory-check":
        _run_memory_check_in_docker(job, source_dir)
        return

    os_name = str(job.get("os", ""))
    compiler = str(job.get("compiler", ""))

    if compiler == "emscripten":
        _run_emscripten_in_docker(job, source_dir)
        return

    host_os = sys.platform

    if compiler == "mingw":
        if host_os == "win32" or (
            shutil.which("x86_64-w64-mingw32-gcc") and shutil.which("wine")
        ):
            pass
        else:
            _run_mingw_in_docker(job, source_dir)
            return

    if compiler == "cygwin":
        if host_os != "win32":
            print(
                f"Skipping Cygwin job: {job.get('name')} (requires Windows/Cygwin host)"
            )
            return

    deps = job.get("deps", "FETCHCONTENT")
    if (
        compiler == "msvc"
        and os_name.startswith("windows")
        and deps == "VCPKG"
        and host_os != "win32"
    ):
        print(
            f"Skipping MSVC Vcpkg job: {job.get('name')} (vcpkg with MSVC requires Windows host)"
        )
        return

    is_msvc = compiler == "msvc" and os_name.startswith("windows")
    is_apple_clang = compiler == "clang" and os_name.startswith("macos")
    is_linux = (
        os_name.startswith("ubuntu") or os_name.startswith("alpine")
    ) and compiler in ("gcc", "clang")

    # Delegate Linux jobs to Docker or WSL if we are not on a Linux host
    if is_linux and host_os != "linux":
        if host_os == "win32" and use_wsl:
            _run_linux_in_wsl(job, source_dir)
        else:
            _run_linux_in_docker(job, source_dir, run_valgrind=run_valgrind)
        return

    # Prevent macOS jobs from running on non-macOS hosts
    if is_apple_clang and host_os != "darwin":
        print(f"Skipping Job: {job.get('name')} (macOS jobs require a macOS host)")
        return

    print(f"Replicating Job: {job.get('name')}")

    build_type = "Debug"
    shared = str(job.get("shared", "OFF"))
    lto = str(job.get("lto", "OFF"))
    charset = str(job.get("charset", "UNICODE"))
    thread = str(job.get("thread", "ON"))
    deps = str(job.get("deps", "FETCHCONTENT"))

    rtc = str(job.get("rtc", "OFF"))
    crt = str(job.get("crt", "MultiThreadedDLL"))

    is_mingw = compiler == "mingw"
    if is_msvc:
        build_dir_name = (
            "build_local_msvc_native" if host_os == "win32" else "build_local_msvc_wine"
        )
    elif is_mingw:
        build_dir_name = "build_local_mingw"
    elif is_apple_clang:
        build_dir_name = "build_local_apple_clang"
    else:
        build_dir_name = f"build_local_linux_{compiler}"

    build_dir = os.path.abspath(os.path.join(source_dir, build_dir_name))
    if os.path.exists(build_dir):
        import time

        for _ in range(5):
            try:
                shutil.rmtree(build_dir)
                break
            except Exception:
                time.sleep(1)
    env = os.environ.copy()

    cmake_args = [
        "cmake",
        "-S",
        source_dir,
        "-B",
        build_dir,
        f"-DCMAKE_BUILD_TYPE={build_type}",
        f"-DBUILD_SHARED_LIBS={shared}",
        f"-DCMAKE_INTERPROCEDURAL_OPTIMIZATION={lto}",
        f"-DCDD_CHARSET={charset}",
        f"-DCDD_THREADING={thread}",
        f"-DCDD_DEPS={deps}",
        "-DBUILD_TESTING=ON",
    ]

    proj_name = os.path.basename(os.path.abspath(source_dir)).replace("-", "_").upper()
    cmake_args.append(f"-D{proj_name}_BUILD_TESTING=ON")
    for dep, dname in [
        ("PARSON", "parson"),
        ("C-ABSTRACT-HTTP", "c-abstract-http"),
        ("C89STRINGUTILS", "c89stringutils"),
        ("CDD-C", "cdd-c"),
        ("CDD_C", "cdd-c"),
        ("C-STR-SPAN", "c-str-span"),
        ("C_STR_SPAN", "c-str-span"),
        ("C-ORM", "c-orm"),
        ("CFS", "c-fs"),
    ]:
        cand = os.path.abspath(os.path.join(source_dir, "..", dname))
        if os.path.exists(cand):
            cmake_args.append(f"-DFETCHCONTENT_SOURCE_DIR_{dep}={cand}")

    if job.get("cmake_configure_flags"):
        import shlex

        cmake_args.extend(shlex.split(job["cmake_configure_flags"]))
    user_vcpkg_toolchain = os.path.expanduser(
        "~/repos/vcpkg/scripts/buildsystems/vcpkg.cmake"
    )
    if deps == "VCPKG" and os.path.exists(user_vcpkg_toolchain):
        cmake_args.append(f"-DCMAKE_TOOLCHAIN_FILE={user_vcpkg_toolchain}")

    if is_msvc:
        if host_os == "win32":
            if not shutil.which("cl"):
                print("Warning: cl.exe not found in PATH.")
            cmake_args.extend(
                [
                    "-DCMAKE_C_COMPILER=cl",
                    "-DCMAKE_CXX_COMPILER=cl",
                    f"-DCDD_MSVC_RTC={rtc}",
                    f"-DCMAKE_MSVC_RUNTIME_LIBRARY={crt}",
                ]
            )
        else:
            msvc_wine_path = os.environ.get("MSVC_WINE_PATH")
            if not msvc_wine_path:
                candidates = [
                    os.path.join(os.path.expanduser("~"), "my_msvc"),
                    os.path.join(os.path.expanduser("~"), "my_msvc", "opt", "msvc"),
                    "/opt/msvc",
                ]
                for candidate in candidates:
                    if os.path.exists(
                        os.path.join(candidate, "bin", "x64", "cl")
                    ) or os.path.exists(
                        os.path.join(candidate, "bin", "x64", "cl.exe")
                    ):
                        msvc_wine_path = candidate
                        break
                if not msvc_wine_path:
                    msvc_wine_path = os.path.join(os.path.expanduser("~"), "my_msvc")

            if not os.path.exists(msvc_wine_path):
                print(f"Error: MSVC_WINE_PATH not found at {msvc_wine_path}")
                sys.exit(1)

            wine_prefix = os.environ.get(
                "WINEPREFIX", os.path.expanduser("~/.wine_cdd_c")
            )
            env["WINEPREFIX"] = wine_prefix
            env["MVK_CONFIG_LOG_LEVEL"] = "0"
            import time

            subprocess.run(["wineserver", "-k"], env=env, stderr=subprocess.DEVNULL)
            subprocess.run(["wineserver", "-w"], env=env, stderr=subprocess.DEVNULL)
            time.sleep(1)
            subprocess.run(["wineserver", "-p"], env=env, stderr=subprocess.DEVNULL)

            cmake_args.extend(
                [
                    "-DCMAKE_SYSTEM_NAME=Windows",
                    "-DCMAKE_C_COMPILER=cl",
                    "-DCMAKE_CXX_COMPILER=cl",
                    "-DCMAKE_CROSSCOMPILING_EMULATOR=wine",
                    "-DCMAKE_LINKER=link",
                    f"-DCDD_MSVC_RTC={rtc}",
                    f"-DCMAKE_MSVC_RUNTIME_LIBRARY={crt}",
                    "-DCMAKE_MSVC_DEBUG_INFORMATION_FORMAT=Embedded",
                ]
            )
            env["PATH"] = f"{msvc_wine_path}/bin/x64:" + env.get("PATH", "")

    elif is_mingw:
        cmake_args.extend(
            [
                "-DCMAKE_SYSTEM_NAME=Windows",
                "-DCMAKE_SYSTEM_PROCESSOR=x86_64",
                "-DTARGET_ARCH=AMD64",
                "-DCMAKE_C_COMPILER=x86_64-w64-mingw32-gcc",
                "-DCMAKE_CXX_COMPILER=x86_64-w64-mingw32-g++",
                "-DCMAKE_CROSSCOMPILING_EMULATOR=wine",
            ]
        )
    elif is_apple_clang:
        cmake_args.extend(
            [
                "-DCMAKE_C_COMPILER=clang",
                "-DCMAKE_CXX_COMPILER=clang++",
            ]
        )

    elif is_linux:
        cc = compiler
        if not shutil.which(cc):
            print(f"Warning: {cc} not found in PATH. Trying fallback...")
            cc = "gcc" if compiler == "clang" else "clang"

        cxx = "clang++" if cc == "clang" else "g++"

        if not shutil.which(cc):
            print("Error: Neither clang nor gcc found on this Linux host.")
            sys.exit(1)

        cmake_args.extend(
            [
                f"-DCMAKE_C_COMPILER={cc}",
                f"-DCMAKE_CXX_COMPILER={cxx}",
            ]
        )

    print(f"\n> Running CMake Configure:\n{' '.join(cmake_args)}")
    stdbuf_cmd = (
        ["stdbuf", "-oL", "-eL"] if shutil.which("stdbuf") else []
    ) + cmake_args
    res = subprocess.run(stdbuf_cmd, env=env)
    if res.returncode != 0:
        print("CMake Configure failed!")
        sys.exit(res.returncode)

    build_args = [
        "cmake",
        "--build",
        build_dir,
        "--config",
        build_type,
        "--parallel",
        "1" if (is_msvc and host_os != "win32") else "4",
    ]
    print(f"\n> Running CMake Build:\n{' '.join(build_args)}")
    res = subprocess.run(build_args, env=env)
    if res.returncode != 0:
        print("CMake Build failed!")
        sys.exit(res.returncode)

    print(f"\n> Running Tests (CTest)")
    ctest_env = env.copy()

    if is_msvc and host_os != "win32":
        winepath_parts = [build_dir, f"{msvc_wine_path}/bin/x64"]
        for rc_dir in [
            f"{msvc_wine_path}/VC/Redist/MSVC/14.51.36231/debug_nonredist/x64/Microsoft.VC145.DebugCRT",
            f"{msvc_wine_path}/VC/Redist/MSVC/14.51.36231/x64/Microsoft.VC145.CRT",
        ]:
            if os.path.exists(rc_dir):
                winepath_parts.append(rc_dir)
                break
        for uc in [
            f"{msvc_wine_path}/Windows Kits/10/bin/10.0.26100.0/x64/ucrt",
            f"{msvc_wine_path}/kits/10/bin/10.0.26100.0/x64/ucrt",
        ]:
            if os.path.exists(uc):
                winepath_parts.append(uc)
                break
        winepath = ";".join(winepath_parts)
        deps_dir = os.path.join(build_dir, "_deps")
        if os.path.exists(deps_dir):
            for dep in os.listdir(deps_dir):
                if dep.endswith("-build"):
                    winepath += f";{os.path.join(deps_dir, dep)}"
        ctest_env["WINEPATH"] = winepath
        ctest_env["_NO_DEBUG_HEAP"] = "1"
        ctest_env["WINEDEBUG"] = "-all"
    elif is_mingw and host_os != "win32":
        mingw_lib_dirs = []
        gcc_path = shutil.which("x86_64-w64-mingw32-gcc")
        if gcc_path:
            res_lib = subprocess.run(
                [gcc_path, "-print-file-name=libgcc_s_seh-1.dll"],
                capture_output=True,
                text=True,
            )
            dll_path = res_lib.stdout.strip()
            if os.path.exists(dll_path):
                mingw_lib_dirs.append(os.path.dirname(dll_path))
                bin_dir = os.path.join(
                    os.path.dirname(os.path.dirname(dll_path)), "bin"
                )
                if os.path.isdir(bin_dir):
                    mingw_lib_dirs.append(bin_dir)
        winepath_parts = [build_dir, os.path.join(build_dir, "bin")] + mingw_lib_dirs
        deps_dir = os.path.join(build_dir, "_deps")
        if os.path.isdir(deps_dir):
            for root, dirs, files in os.walk(deps_dir):
                if any(f.endswith(".dll") for f in files):
                    winepath_parts.append(root)
        ctest_env["WINEPATH"] = ";".join(winepath_parts)
    elif is_msvc and host_os == "win32":
        ctest_env["_NO_DEBUG_HEAP"] = "1"
        ctest_env["WINEDEBUG"] = "-all"

    ctest_args = ["ctest", "-C", build_type, "--output-on-failure"]
    res = subprocess.run(ctest_args, cwd=build_dir, env=ctest_env)

    if res.returncode != 0:
        print("\nTests failed!")
        sys.exit(res.returncode)
    else:
        print("\nAll tests passed successfully!")


def main() -> None:
    """
    Main entry point for the replication script.
    """
    parser = argparse.ArgumentParser(
        description="Replicate GitHub Actions matrix runs locally"
    )
    parser.add_argument(
        "--yaml",
        default=None,
        help="Path to workflow YAML (c-cmake-ci.yml or project ci.yml)",
    )
    parser.add_argument(
        "--source", default=".", help="Path to the source directory to build"
    )
    parser.add_argument(
        "--list", action="store_true", help="List available jobs from the workflow"
    )
    parser.add_argument("--run", type=int, help="Index of the job to run")
    parser.add_argument(
        "--all", action="store_true", help="Run all available jobs sequentially"
    )
    parser.add_argument(
        "--wsl",
        action="store_true",
        help="Use WSL instead of Docker for Linux jobs (Windows hosts only)",
    )
    parser.add_argument(
        "--no-valgrind",
        action="store_true",
        help="Skip running Valgrind memcheck on Linux jobs",
    )

    args = parser.parse_args()

    if args.yaml is None:
        proj_ci = os.path.join(args.source, ".github", "workflows", "ci.yml")
        if os.path.exists(proj_ci):
            args.yaml = proj_ci
        else:
            args.yaml = os.path.join(
                os.path.dirname(__file__), ".github", "workflows", "c-cmake-ci.yml"
            )

    if not os.path.exists(args.yaml):
        print(f"Error: Workflow YAML not found at {args.yaml}")
        sys.exit(1)

    jobs = load_matrix(args.yaml)
    if not jobs:
        print("No jobs found in the matrix.")
        sys.exit(0)

    if args.list:
        print_jobs(jobs)
        sys.exit(0)

    run_valgrind = not args.no_valgrind

    if args.all:
        failed_jobs = []
        for i, job in enumerate(jobs):
            print(f"\n============================================================")
            print(f"Running Job [{i}]: {job.get('name')}")
            print(f"============================================================")
            try:
                run_job(job, args.source, use_wsl=args.wsl, run_valgrind=run_valgrind)
            except SystemExit as e:
                if e.code != 0:
                    failed_jobs.append((i, job.get("name"), e.code))
        if failed_jobs:
            print("\nSummary of Failed Jobs:")
            for idx, name, code in failed_jobs:
                print(f"  [{idx}] {name} (exit code: {code})")
            sys.exit(1)
        else:
            print("\nAll jobs in matrix succeeded!")
    elif args.run is not None:
        if args.run < 0 or args.run >= len(jobs):
            print(f"Invalid job index. Choose a number between 0 and {len(jobs) - 1}.")
            sys.exit(1)
        run_job(
            jobs[args.run], args.source, use_wsl=args.wsl, run_valgrind=run_valgrind
        )
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  ./replicate_gh_matrix.py --list")
        print(f"  ./replicate_gh_matrix.py --run 0 --source ..{os.path.sep}c-str-span")
        print(f"  ./replicate_gh_matrix.py --all --source ..{os.path.sep}c-str-span")
        print(
            "  ./replicate_gh_matrix.py --run 4 --wsl  # Runs a Linux job via WSL on Windows"
        )


if __name__ == "__main__":
    main()
