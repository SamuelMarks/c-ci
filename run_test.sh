#!/bin/sh
cd /home/samuel/repos/c-rest-framework
pre-commit run build-msvc-2005-wine --all-files > pcout.txt 2>&1
echo "Done"
