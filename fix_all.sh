#!/bin/sh
for repo in ../c-abstract-http ../c-fs ../c-orm ../c-rest-framework ../c-str-span ../c89stringutils ../cdd-c; do
  (
    cd "$repo" || exit 0
    rm -f build_msvc2005_wine.cmd build_msvc2026_wine.cmd
    git rm --ignore-unmatch build_msvc2005_wine.cmd build_msvc2026_wine.cmd || true
    git commit -m "Remove legacy local msvc scripts" || true
    # git push || true (disabled per instructions)
  )
done
