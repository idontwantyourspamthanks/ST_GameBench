#!/bin/bash
# usage: run_state.sh  -> res/st_*.json + res/state_log.txt ; sequential Hatari state gates (stock A vs final T tick on, X extras 16/32)
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint
L=res/state_log.txt
run() { echo "== $*" >> $L; timeout 3000 python3 exp_state_int.py "$@" >> $L 2>&1; }
run A ste1m_race_start.sav 8 220 res/st_start_A8.json
run T ste1m_race_start.sav 8 220 res/st_start_T8.json
run A ste1m_race_drive.sav 8 300 res/st_drive_A8.json
run T ste1m_race_drive.sav 8 300 res/st_drive_T8.json
run X ste1m_race_start.sav 16 220 res/st_start_X16.json
run X ste1m_race_start.sav 32 220 res/st_start_X32.json
run X ste1m_race_drive.sav 16 300 res/st_drive_X16.json
echo ALLDONE >> $L
