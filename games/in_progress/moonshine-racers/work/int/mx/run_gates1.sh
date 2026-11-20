#!/usr/bin/env bash
cd "$(dirname "$0")"
for v in "A 8" "T 8" "X 8" "X 16" "X 32"; do set -- $v; python3 exp_state.py $1 ste1m_race_drive.sav $2 270 res/st_drive_$1$2.json 2>&1 | tail -1; done
mkdir -p pix
for sc in race_start race_drive; do
 for v in "A 8" "T 8" "X 8" "X 16" "X 32"; do set -- $v; python3 pixcap.py $1 ste1m_$sc.sav $2 200 pix/${sc}_$1$2 2>&1 | tail -1; done
done
echo DONE
