FROM alpine:latest

RUN apk add --no-cache \
    build-base \
    bash \
    cmake \
    clang \
    curl \
    zip \
    perl \
    unzip \
    tar \
    curl-dev \
    git \
    pkgconf \
    openssl-dev \
    sqlite \
    sqlite-dev \
    valgrind \
    gdb \
    ninja \
    linux-headers

WORKDIR /workspace
