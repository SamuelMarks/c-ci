FROM alpine:latest

RUN pkgs="build-base bash cmake clang curl zip perl unzip tar curl-dev git pkgconf openssl-dev sqlite sqlite-dev valgrind gdb ninja linux-headers" && \
    to_install="" && \
    for pkg in $pkgs; do \
        if ! apk info -e "$pkg" >/dev/null 2>&1; then \
            to_install="$to_install $pkg"; \
        fi; \
    done && \
    if [ -n "$to_install" ]; then \
        apk add --no-cache $to_install; \
    fi

WORKDIR /workspace
