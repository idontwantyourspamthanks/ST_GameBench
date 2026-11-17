#!/bin/sh
# private patch dir: every patches/*.s and support file except other agents' ta_* / tc_* (in-progress, may not verify) + work/tightB/variants/*.s
cd "$(dirname "$0")"; rm -rf patches; mkdir patches
for f in ../../patches/*; do b=$(basename "$f"); case "$b" in ta_*|tc_*) ;; *) ln -s "../$f" "patches/$b";; esac; done
for f in variants/*.s; do [ -e "$f" ] && ln -s "../$f" "patches/$(basename $f)"; done
true
