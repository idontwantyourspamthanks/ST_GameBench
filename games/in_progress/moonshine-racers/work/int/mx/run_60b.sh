#!/usr/bin/env bash
cd "$(dirname "$0")"
for v in "A 8" "T 8" "X 8" "X 16" "X 32"; do set -- $v; python3 exp_state.py $1 ste1m_race_start.sav $2 200 res/st_60f_$1$2.json hz60 2>&1 | tail -1; done
for v in "A 8" "T 8" "X 16" "X 32"; do set -- $v; python3 pixcap.py $1 ste1m_race_start.sav $2 200 pix/f60_$1$2 40 hz60 2>&1 | tail -1; done
echo DONE60
echo "=== 5-minute play STE 1 MB 8 MHz"; python3 play5.py ste 1024 1.62 build/mx_hd 8 16700 2>&1 | tail -30
echo "=== 5-minute play STE 1 MB 16 MHz"; python3 play5.py ste 1024 1.62 build/mx_hd 16 16700 2>&1 | tail -30
echo DONE
