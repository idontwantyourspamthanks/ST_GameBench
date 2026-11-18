#!/usr/bin/env bash
cd "$(dirname "$0")"
mkdir -p pix
for L in 5 12; do
  for v in "A 8" "X 16" "X 32"; do set -- $v; python3 exp_state.py $1 ste1m_race_drive.sav $2 560 res/st_L${L}_$1$2.json 102c=$(printf %04x $L) 6105=01 hold kern 2>&1 | tail -1; done
done
echo DONE
