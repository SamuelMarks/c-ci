FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    pkgs="build-essential cmake clang curl zip perl unzip tar bison flex libcurl4-openssl-dev git pkg-config libssl-dev sqlite3 libsqlite3-dev valgrind gdb ninja-build gcc-mingw-w64-x86-64 g++-mingw-w64-x86-64 wine wine64" && \
    to_install="" && \
    for pkg in $pkgs; do \
        if ! dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -q "ok installed"; then \
            to_install="$to_install $pkg"; \
        fi; \
    done && \
    if [ -n "$to_install" ]; then \
        apt-get install -y $to_install; \
    fi && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
