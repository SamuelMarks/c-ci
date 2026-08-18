#!/bin/sh
if [ "$(uname)" = "Darwin" ]; then
    cd "$HOME/repos/c-rest-framework" || exit 1
else
    cd /home/samuel/repos/c-rest-framework || exit 1
fi
pre-commit run build-msvc-2005-wine --all-files > pcout.txt 2>&1
echo "Done"
