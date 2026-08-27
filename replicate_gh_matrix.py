#!/usr/bin/env python3
"""
Replicate GitHub Actions matrix runs locally.

This script parses a GitHub Actions workflow YAML file to extract the matrix of jobs,
and allows running specific MSVC, Apple Clang, or Linux GCC/Clang jobs locally
to replicate CI behavior without needing to push to GitHub.

It handles cross-platform execution intelligently:
- Runs macOS jobs natively on macOS.
- Runs MSVC jobs natively on Windows, or via WINE on Unix-like systems.
- Runs Linux jobs natively on Linux (with automatic clang/gcc fallbacks),
  via Docker on non-Linux systems, or via WSL (Windows Subsystem for Linux) on Windows.
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
    Load the GitHub Actions workflow YAML and extract supported matrix jobs.

    This filters the full GitHub Actions matrix to include only the jobs we
    can reliably replicate locally (Windows MSVC, macOS Clang, and Linux GCC/Clang).

    Args:
        yaml_path (str): The file path to the GitHub Actions workflow YAML file.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries, where each dictionary represents
                              a supported job from the matrix.
    """
    with open(yaml_path, "r") as f:
        workflow = yaml.safe_load(f)

    matrix_includes = (
        workflow.get("jobs", {})
        .get("build-and-test", {})
        .get("strategy", {})
        .get("matrix", {})
        .get("include", [])
    )

    # Filter for Windows MSVC jobs, macOS Clang jobs, and Linux GCC/Clang jobs
    supported_jobs = [
        job
        for job in matrix_includes
        if (
            job.get("compiler") == "msvc"
            and str(job.get("os", "")).startswith("windows")
        )
        or (
            job.get("compiler") == "clang"
            and str(job.get("os", "")).startswith("macos")
        )
        or (
            job.get("compiler") in ("gcc", "clang")
            and (
                str(job.get("os", "")).startswith("ubuntu")
                or str(job.get("os", "")).startswith("alpine")
            )
        )
    ]
    return supported_jobs


def print_jobs(jobs: List[Dict[str, Any]]) -> None:
    """
    Print the list of available jobs to the console.

    Iterates through the list of supported jobs and displays their index
    and descriptive name, making it easy for the user to select one to run.

    Args:
        jobs (List[Dict[str, Any]]): A list of dictionaries containing job configurations.

    Returns:
        None
    """
    print("Available Matrix Jobs (MSVC, AppleClang, Linux GCC/Clang):")
    print("-" * 60)
    for i, job in enumerate(jobs):
        print(f"[{i}] {job.get('name')}")
    print("-" * 60)


def _run_linux_in_docker(job: Dict[str, Any], source_dir: str) -> None:
    """
    Run a Linux CI job inside a Docker container.

    This is invoked when testing Linux GCC or Clang jobs on a non-Linux host
    (e.g., Windows or macOS). It mounts the local source directory into an Ubuntu
    container, installs dependencies, and runs CMake configure, build, and CTest.

    Args:
        job (Dict[str, Any]): The job configuration dictionary extracted from the YAML matrix.
        source_dir (str): The path to the source directory containing the CMakeLists.txt.

    Returns:
        None
    """
    print(f"Replicating Job in Docker: {job.get('name')}")
    if not shutil.which("docker"):
        print("Error: 'docker' is required but not found in PATH.")
        sys.exit(1)

    # Check if the Docker daemon/socket is responsive
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

    build_dir_name = f"build_docker_{compiler}"
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

    build_args = [
        "cmake",
        "--build",
        container_build,
        "--config",
        build_type,
        "--parallel",
        "4",
    ]
    ctest_args = ["ctest", "-C", build_type, "--output-on-failure"]

    os_name = str(job.get("os", ""))
    is_alpine = os_name.startswith("alpine")

    if is_alpine:
        image = "alpine:latest"
        pkg_cmd = "apk add --no-cache cmake build-base clang dos2unix sqlite-dev valgrind linux-headers bash"
    else:
        image = "ubuntu:22.04"
        pkg_cmd = "apt-get update -yqq && apt-get install -yqq cmake gcc g++ clang dos2unix libsqlite3-dev valgrind"

    # Constructing a single bash string to run inside the container
    cmd_str = (
        f"{pkg_cmd} && "
        + " ".join(cmake_args)
        + " && "
        + " ".join(build_args)
        + " && "
        + f"cd {container_build} && "
        + " ".join(ctest_args)
    )

    docker_cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{os.path.abspath(source_dir)}:{container_src}",
        "-w",
        container_src,
        image,
        "sh",
        "-c",
        cmd_str,
    ]

    print(f"\n> Executing Docker command:\n{' '.join(docker_cmd)}")
    res = subprocess.run(docker_cmd)
    if res.returncode != 0:
        print("\nDocker execution failed!")
        sys.exit(res.returncode)
    else:
        print("\nAll tests passed successfully in Docker!")


def _run_linux_in_wsl(job: Dict[str, Any], source_dir: str) -> None:
    """
    Run a Linux CI job using Windows Subsystem for Linux (WSL).

    This assumes the default WSL distribution has cmake and the necessary
    toolchains installed. It executes the build inside the WSL environment
    using relative paths mapped directly from the Windows working directory.

    Args:
        job (Dict[str, Any]): The job configuration dictionary extracted from the YAML matrix.
        source_dir (str): The path to the source directory containing the CMakeLists.txt.

    Returns:
        None
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

    build_dir_name = f"build_wsl_{compiler}"

    proj_name = os.path.basename(os.path.abspath(source_dir)).replace("-", "_").upper()
    cc = compiler
    cxx = "clang++" if cc == "clang" else "g++"

    # Note: In WSL, we use relative paths ('.') to avoid C:\ path conversion issues,
    # as subprocess.run natively starts `wsl` in the equivalent mapped directory.
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
        "4",
    ]
    ctest_args = ["ctest", "-C", build_type, "--output-on-failure"]

    # We do not run apt-get here to avoid sudo password prompts.
    # It is expected that the user has a configured C/C++ environment in WSL.
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
    # Using cwd=source_dir lets WSL translate the context seamlessly
    res = subprocess.run(wsl_cmd, cwd=source_dir)
    if res.returncode != 0:
        print(
            "\nWSL execution failed! (Ensure cmake and the compiler are installed in your default WSL distro)"
        )
        sys.exit(res.returncode)
    else:
        print("\nAll tests passed successfully in WSL!")


def run_job(job: Dict[str, Any], source_dir: str, use_wsl: bool = False) -> None:
    """
    Run a specific job locally by constructing and executing CMake commands.

    This handles the native execution for macOS Clang, Windows MSVC natively,
    Linux natively (with clang/gcc fallback), and MSVC via WINE on Unix-like hosts.
    If a Linux job is requested on a non-Linux host, it delegates to Docker (or WSL if requested).

    Args:
        job (Dict[str, Any]): The job configuration dictionary extracted from the YAML matrix.
        source_dir (str): The path to the source directory containing the CMakeLists.txt.
        use_wsl (bool): Whether to use WSL instead of Docker for Linux jobs (Windows hosts only).

    Returns:
        None
    """
    os_name = str(job.get("os", ""))
    compiler = str(job.get("compiler", ""))

    is_msvc = compiler == "msvc" and os_name.startswith("windows")
    is_apple_clang = compiler == "clang" and os_name.startswith("macos")
    is_linux = (
        os_name.startswith("ubuntu") or os_name.startswith("alpine")
    ) and compiler in ("gcc", "clang")

    host_os = sys.platform

    # Delegate Linux jobs to Docker or WSL if we are not on a Linux host
    if is_linux and host_os != "linux":
        if host_os == "win32" and use_wsl:
            _run_linux_in_wsl(job, source_dir)
        else:
            _run_linux_in_docker(job, source_dir)
        return

    # Prevent macOS jobs from running on non-macOS hosts
    if is_apple_clang and host_os != "darwin":
        print(f"Skipping Job: {job.get('name')} (macOS jobs require a macOS host)")
        return

    print(f"Replicating Job: {job.get('name')}")

    # Defaults from workflow inputs
    build_type = "Debug"
    shared = str(job.get("shared", "OFF"))
    lto = str(job.get("lto", "OFF"))
    charset = str(job.get("charset", "UNICODE"))
    thread = str(job.get("thread", "ON"))
    deps = str(job.get("deps", "FETCHCONTENT"))

    # MSVC Specifics
    rtc = str(job.get("rtc", "OFF"))
    crt = str(job.get("crt", "MultiThreadedDLL"))

    # Determine local build directory based on environment and compiler
    if is_msvc:
        build_dir_name = (
            "build_local_msvc_native" if host_os == "win32" else "build_local_msvc_wine"
        )
    elif is_apple_clang:
        build_dir_name = "build_local_apple_clang"
    else:  # is_linux natively
        build_dir_name = f"build_local_linux_{compiler}"

    build_dir = os.path.abspath(os.path.join(source_dir, build_dir_name))
    env = os.environ.copy()

    # Construct shared CMake Configuration Arguments
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

    # Add project-specific TEST flag if guessing project name from dir
    proj_name = os.path.basename(os.path.abspath(source_dir)).replace("-", "_").upper()
    cmake_args.append(f"-D{proj_name}_BUILD_TESTING=ON")

    if is_msvc:
        if host_os == "win32":
            # Run completely natively on Windows
            if not shutil.which("cl"):
                print(
                    "Warning: cl.exe not found in PATH. Please run this script from an MSVC Developer Command Prompt."
                )
            cmake_args.extend(
                [
                    "-DCMAKE_C_COMPILER=cl",
                    "-DCMAKE_CXX_COMPILER=cl",
                    f"-DCDD_MSVC_RTC={rtc}",
                    f"-DCMAKE_MSVC_RUNTIME_LIBRARY={crt}",
                ]
            )
        else:
            # Run via WINE on Unix-like host
            msvc_wine_path = os.environ.get(
                "MSVC_WINE_PATH",
                os.path.join(os.path.expanduser("~"), "my_msvc", "opt", "msvc"),
            )
            if not os.path.exists(msvc_wine_path):
                print(f"Error: MSVC_WINE_PATH not found at {msvc_wine_path}")
                print("Please set MSVC_WINE_PATH to your local MSVC installation.")
                sys.exit(1)

            # Initialize WINE
            subprocess.run(["wineserver", "-k"], stderr=subprocess.DEVNULL)
            subprocess.run(["wineserver", "-p"])

            cmake_args.extend(
                [
                    "-DCMAKE_SYSTEM_NAME=Windows",
                    "-DCMAKE_C_COMPILER=cl",
                    "-DCMAKE_CXX_COMPILER=cl",
                    "-DCMAKE_CROSSCOMPILING_EMULATOR=wine",
                    "-DCMAKE_LINKER=link",
                    f"-DCDD_MSVC_RTC={rtc}",
                    f"-DCMAKE_MSVC_RUNTIME_LIBRARY={crt}",
                ]
            )
            env["PATH"] = f"{msvc_wine_path}/bin/x64:" + env.get("PATH", "")

    elif is_apple_clang:
        cmake_args.extend(
            [
                "-DCMAKE_C_COMPILER=clang",
                "-DCMAKE_CXX_COMPILER=clang++",
            ]
        )

    elif is_linux:
        # Run natively on Linux
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

    # Run CMake Configuration
    print(f"\n> Running CMake Configure:\n{' '.join(cmake_args)}")
    res = subprocess.run(cmake_args, env=env)
    if res.returncode != 0:
        print("CMake Configure failed!")
        sys.exit(res.returncode)

    # Run CMake Build
    build_args = [
        "cmake",
        "--build",
        build_dir,
        "--config",
        build_type,
        "--parallel",
        "4",
    ]
    print(f"\n> Running CMake Build:\n{' '.join(build_args)}")
    res = subprocess.run(build_args, env=env)
    if res.returncode != 0:
        print("CMake Build failed!")
        sys.exit(res.returncode)

    # Run CTest
    print(f"\n> Running Tests (CTest)")
    ctest_env = env.copy()

    if is_msvc and host_os != "win32":
        # Add WINEPATH for CTest executing Windows binaries via WINE
        winepath = f"{build_dir};{msvc_wine_path}/bin/x64;{msvc_wine_path}/VC/Redist/MSVC/14.51.36231/debug_nonredist/x64/Microsoft.VC145.DebugCRT;{msvc_wine_path}/Windows Kits/10/bin/10.0.26100.0/x64/ucrt"
        deps_dir = os.path.join(build_dir, "_deps")
        if os.path.exists(deps_dir):
            for dep in os.listdir(deps_dir):
                if dep.endswith("-build"):
                    winepath += f";{os.path.join(deps_dir, dep)}"
        ctest_env["WINEPATH"] = winepath
        ctest_env["_NO_DEBUG_HEAP"] = "1"
    elif is_msvc and host_os == "win32":
        # Suppress MSVC UI debug dialogs when running natively on Windows
        ctest_env["_NO_DEBUG_HEAP"] = "1"

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

    Parses command-line arguments to specify the YAML workflow path and target source directory.
    Provides options to either list available jobs from the parsed workflow or execute a
    specific job based on its index.

    Returns:
        None
    """
    parser = argparse.ArgumentParser(
        description="Replicate GitHub Actions MSVC/AppleClang/Linux runs locally"
    )
    parser.add_argument(
        "--yaml",
        default=os.path.join(
            os.path.dirname(__file__), ".github", "workflows", "c-cmake-ci.yml"
        ),
        help="Path to the shared workflow YAML",
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

    args = parser.parse_args()

    if not os.path.exists(args.yaml):
        print(f"Error: Workflow YAML not found at {args.yaml}")
        print("Provide the path to c-cmake-ci.yml using --yaml")
        sys.exit(1)

    jobs = load_matrix(args.yaml)
    if not jobs:
        print("No supported jobs found in the matrix.")
        sys.exit(0)

    if args.list:
        print_jobs(jobs)
        sys.exit(0)

    if args.all:
        for i, job in enumerate(jobs):
            print(f"\n============================================================")
            print(f"Running Job [{i}]: {job.get('name')}")
            print(f"============================================================")
            run_job(job, args.source, use_wsl=args.wsl)
    elif args.run is not None:
        if args.run < 0 or args.run >= len(jobs):
            print(f"Invalid job index. Choose a number between 0 and {len(jobs) - 1}.")
            sys.exit(1)
        run_job(jobs[args.run], args.source, use_wsl=args.wsl)
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
