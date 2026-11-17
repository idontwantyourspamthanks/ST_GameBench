#!/bin/bash
# Per-pass state ($7b86 after the flip, keyed by $100e) stock vs the integrated default (X: tick ON + mg extras) at 8/16/32 MHz.
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2
L=res/state_log.txt
run() { echo "== $*" >> $L; timeout 3000 python3 exp_state_fin.py "$@" >> $L 2>&1; }
# unsteered: race_start (driving from the snapshot), race_drive (time-out sequence + restart inside, keys 0..1706)
run A ste1m_race_start.sav 8 230 res/st_start_A8.json
run X ste1m_race_start.sav 8 230 res/st_start_X8.json
run X ste1m_race_start.sav 16 230 res/st_start_X16.json
run X ste1m_race_start.sav 32 230 res/st_start_X32.json
run A ste1m_race_drive.sav 8 320 res/st_drive_A8.json
run X ste1m_race_drive.sav 8 320 res/st_drive_X8.json
run X ste1m_race_drive.sav 16 320 res/st_drive_X16.json
run X ste1m_race_drive.sav 32 320 res/st_drive_X32.json
# steered (zig: up / up+left / up / up+right, 15 passes each, a pure function of $100e): tb_car draws a changing bitmap
run A ste1m_race_start.sav 8 260 res/st_zig_start_A8.json zig=140
run X ste1m_race_start.sav 8 260 res/st_zig_start_X8.json zig=140
run X ste1m_race_start.sav 16 260 res/st_zig_start_X16.json zig=140
run X ste1m_race_start.sav 32 260 res/st_zig_start_X32.json zig=140
run A ste1m_race_up.sav 8 260 res/st_zig_up_A8.json zig=470
run X ste1m_race_up.sav 8 260 res/st_zig_up_X8.json zig=470
run X ste1m_race_up.sav 16 260 res/st_zig_up_X16.json zig=470
run X ste1m_race_up.sav 32 260 res/st_zig_up_X32.json zig=470
echo ALLDONE >> $L
touch res/state.done
