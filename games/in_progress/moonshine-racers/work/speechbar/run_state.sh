#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
R=work/speechbar/res; L=$R/state_log.txt
run() { echo "== $*" >> $L; timeout 3000 python3 work/speechbar/exp_state_sb.py "$@" >> $L 2>&1; }
run A ste1m_race_start.sav 8 260 $R/st_start_A8.json zig=140
run TS ste1m_race_start.sav 8 260 $R/st_start_TS8.json zig=140
run XS ste1m_race_start.sav 16 260 $R/st_start_XS16.json zig=140
run XS ste1m_race_start.sav 32 260 $R/st_start_XS32.json zig=140
run A ste1m_race_drive.sav 8 300 $R/st_drive_A8.json
run TS ste1m_race_drive.sav 8 300 $R/st_drive_TS8.json
run XS ste1m_race_drive.sav 16 300 $R/st_drive_XS16.json
echo DONE >> $L
