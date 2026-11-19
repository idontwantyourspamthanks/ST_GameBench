#!/usr/bin/env bash
# Gate (b): the full floppy cells (boot -> swap to FFB -> M/J/K -> hall -> personnel -> map -> boss -> 3D view -> walk/turn -> soak), one Hatari at a time.
# Argument 1: disk dir (dev build or the unzipped shipped zip); argument 2: name prefix; argument 3: cell list (default all).
cd "$(dirname "$0")"
D=${1:-/tmp/mw2f/b16}; P=${2:-c}; EXT=${EXT:-st}
run() { n=$1; shift; timeout 1500 python3 cell16.py "$n" "$@" --ext $EXT > "out/$n.log" 2>&1; grep -E "^(CELL|EXC)|REACHED|first game restore|game type I commands" "out/$n.log" | cut -c1-240; }
run ${P}_ste162_8_d2    ste     162 1024 $D 8  2 --soak 120
run ${P}_ste162_8_d1    ste     162 1024 $D 8  1
run ${P}_mste206_8_d1   megaste 206 1024 $D 8  1
run ${P}_mste206_16_d1  megaste 206 1024 $D 16 1 --soak 120
run ${P}_mste206_16_d2  megaste 206 1024 $D 16 2
run ${P}_st104_8_d1     st      104 1024 $D 8  1
run ${P}_tt306_d1       tt      306 4096 $D 8  1
