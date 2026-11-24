#!/usr/bin/env bash
cd "$(dirname "$0")"
S=megaste4m_60hz_boot.sav; M=megaste60
for v in "A 8" "T 8" "X 8" "X 16" "X 32"; do set -- $v; python3 exp_state.py $1 $S $2 300 res/st_60_$1$2.json 6105=01 hold $M 2>&1 | tail -1; done
for v in "A 8" "T 8" "X 16" "X 32"; do set -- $v; python3 pixcap.py $1 $S $2 200 pix/s60_$1$2 40 6105=01 hold $M 2>&1 | tail -1; done
echo DONE
