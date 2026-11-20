#!/usr/bin/env bash
cd "$(dirname "$0")"
while pgrep -f "[b]atch_b.sh|[r]un_rest.sh|[r]erun_c.sh" >/dev/null; do sleep 10; done
for spec in "c_ste162_8_d1 ste 162 1024 /tmp/mw2f/b16 8 1" "c_mste206_8_d1 megaste 206 1024 /tmp/mw2f/b16 8 1" "c_mste206_16_d2r megaste 206 1024 /tmp/mw2f/b16 16 2"; do
  set -- $spec; n=$1
  timeout 1500 python3 cell16.py "$@" --ext st > out/$n.log 2>&1; grep -E "^(CELL|EXC)|game type I commands" out/$n.log
done > out/rerun_cells.log 2>&1
./ship_gates.sh ../../dist/Midwinter2_v1.6_patched_floppies_2026-11-19.zip > out/ship_gates.log 2>&1
