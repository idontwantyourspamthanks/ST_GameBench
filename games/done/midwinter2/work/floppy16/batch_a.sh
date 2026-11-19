#!/usr/bin/env bash
# Gate (a): first game restore, on the dev build /tmp/mw2f/b16 (or the shipped zip contents) and the controls.  One Hatari at a time.
cd "$(dirname "$0")"
D=${1:-/tmp/mw2f/b16}; P=${2:-g}
run() { timeout 700 python3 bootgate.py "$@" > "out/$1.log" 2>&1; tail -3 "out/$1.log" | head -2; }
run ${P}_ste8_v16    ste 8      $D --expect pass
run ${P}_mste8_v16   megaste 8  $D --expect pass
run ${P}_mste16_v16  megaste 16 $D --expect pass
if [ "$P" = g ]; then
run ${P}_ste8_v14    ste 8      /tmp/mw2f/v14 --expect fail
run ${P}_mste16_v14  megaste 16 /tmp/mw2f/v14 --expect fail
run ${P}_mste16_nowait megaste 16 /tmp/mw2f/v16_nowait --expect fail
run ${P}_ste8_v15    ste 8      /tmp/mw2f/v15 --expect pass
run ${P}_mste16_v15  megaste 16 /tmp/mw2f/v15 --expect any
run ${P}_mste16_nopark megaste 16 /tmp/mw2f/v16_nopark --expect any
fi
