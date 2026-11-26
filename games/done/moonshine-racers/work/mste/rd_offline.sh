#!/bin/bash
cd "$(dirname "$0")/../road"
for c in "geom_test.py live_geom 60" "geom_fuzz.py live_geom 2100 1" "geom_fuzz.py live_geom 200 1 neg" "geom_reuse_test.py live_geom" "geom_sigtest.py live_geom" "draw_test.py live_draw 60" "draw_fuzz.py live_draw 900 1" "draw_fuzz.py live_draw 100 1 neg"; do
  echo "=== $c"; timeout 3000 python3 $c 2>&1 | tail -6
done
