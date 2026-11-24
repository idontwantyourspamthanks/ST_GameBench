#!/usr/bin/env bash
cd "$(dirname "$0")"
for v in A T X; do for m in 8 16 32; do python3 exp_rate.py $v ste1m_race_start.sav $m 600 2>&1 | tail -1; done; done > res/rates_50hz.txt
for v in A T X; do for m in 8 32; do python3 exp_rate.py $v ste1m_race_start.sav $m 600 hz60 2>&1 | tail -1; done; done > res/rates_60hz.txt
for v in A T X; do for m in 8 16 32; do python3 exp_rate.py $v ste1m_race_grid.sav $m 600 2>&1 | tail -1; done; done > res/rates_grid.txt
for v in "A 8" "X 16" "X 32"; do set -- $v; python3 exp_state.py $1 ste1m_race_drive.sav $2 520 res/st_driveup450_$1$2.json 6105=01 2>&1 | tail -1; done
echo DONE
