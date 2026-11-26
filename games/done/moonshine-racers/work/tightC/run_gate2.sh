#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tightC
L=res/gate_log2.txt
run() { echo "== $*" >> $L; timeout 1700 python3 exp_state_tc.py "$@" >> $L 2>&1; }
run TC ste1m_race_start.sav 8 200 res/st_start_TC8.json
run XC ste1m_race_start.sav 16 200 res/st_start_XC16.json
run XC ste1m_race_start.sav 32 200 res/st_start_XC32.json
run TC ste1m_race_drive.sav 8 270 res/st_drive_TC8.json
run XC ste1m_race_drive.sav 16 270 res/st_drive_XC16.json
echo ALLDONE >> $L
