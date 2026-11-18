#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint
while [ ! -f res/all.done ]; do sleep 10; done
L=res/state_log4.txt
run() { echo "== $*" >> $L; timeout 3000 python3 exp_state_int.py "$@" >> $L 2>&1; }
run A ste1m_race_start.sav 8 260 res/st_zig_start_A8.json zig=140
run T ste1m_race_start.sav 8 260 res/st_zig_start_T8.json zig=140
run X ste1m_race_start.sav 16 260 res/st_zig_start_X16.json zig=140
run X ste1m_race_start.sav 32 260 res/st_zig_start_X32.json zig=140
run A ste1m_race_up.sav 8 260 res/st_zig_up_A8.json zig=470
run T ste1m_race_up.sav 8 260 res/st_zig_up_T8.json zig=470
run X ste1m_race_up.sav 16 260 res/st_zig_up_X16.json zig=470
echo ALLDONE >> $L
echo DONE_Q7 > res/q7.done
