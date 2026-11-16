#!/usr/bin/env bash
cd "$(dirname "$0")"
mkdir -p pix
for v in "A 8" "T 8" "X 8" "X 16" "X 32"; do set -- $v; python3 exp_state.py $1 ste1m_race_drive.sav $2 270 res/st_driveup_$1$2.json 6105=01 2>&1 | tail -1; done
for v in "A 8" "T 8" "X 8" "X 16" "X 32"; do set -- $v; python3 pixcap.py $1 ste1m_race_start.sav $2 200 pix/start_$1$2 2>&1 | tail -1; done
for v in "A 8" "T 8" "X 8" "X 16" "X 32"; do set -- $v; python3 pixcap.py $1 ste1m_race_drive.sav $2 230 pix/driveup_$1$2 40 6105=01 2>&1 | tail -1; done
echo DONE
