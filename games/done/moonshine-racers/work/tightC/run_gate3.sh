#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tightC
L=res/gate_log3.txt
run() { echo "== $*" >> $L; timeout 1700 python3 exp_state_tc.py "$@" >> $L 2>&1; }
run X ste1m_race_start.sav 16 200 res/st_start_X16.json
run X ste1m_race_start.sav 32 200 res/st_start_X32.json
run X ste1m_race_drive.sav 16 270 res/st_drive_X16.json
echo ALLDONE >> $L
