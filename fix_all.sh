#!/bin/sh
for repo in ../c-abstract-http ../c-fs ../c-orm ../c-rest-framework ../c-str-span ../c89stringutils ../cdd-c; do
  cd $repo
  rm -f build_msvc2005_wine.cmd build_msvc2026_wine.cmd
  git rm --ignore-unmatch build_msvc2005_wine.cmd build_msvc2026_wine.cmd
  git commit -m "Remove legacy local msvc scripts" || true
  git push || true
  cd -
done
