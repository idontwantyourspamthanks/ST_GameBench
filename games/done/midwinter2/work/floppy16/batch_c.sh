#!/usr/bin/env bash
# Gate (c): swap behaviour, single and two drives, v1.6 against v1.5 (STE 8 MHz).  Argument 1: the v1.6 disk dir; argument 2: name prefix.
cd "$(dirname "$0")"
D=${1:-/tmp/mw2f/b16}; P=${2:-s}
run() { n=$1; shift; timeout 900 python3 swapgate.py "$n" "$@" > "out/$n.log" 2>&1; grep "SWAP" "out/$n.log"; }
run ${P}_ste_d1_v16  ste 162 8 1  $D A B
run ${P}_ste_d1_v16c ste 162 8 1  $D C CB
run ${P}_ste_d2_v16  ste 162 8 2  $D A B
run ${P}_ste_d2f_v16 ste 162 8 2f $D D
if [ "$P" = s ]; then
run ${P}_ste_d1_v15  ste 162 8 1  /tmp/mw2f/v15 A B
run ${P}_ste_d1_nonflops ste 162 8 1 /tmp/mw2f/v16_nonflops A B
run ${P}_ste_d2_v15  ste 162 8 2  /tmp/mw2f/v15 A B
run ${P}_ste_d2f_v15 ste 162 8 2f /tmp/mw2f/v15 D
fi
