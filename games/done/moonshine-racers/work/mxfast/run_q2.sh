#!/bin/bash
# state gates (Hatari, per pass at $7b86): stock 8 MHz vs mf 16/32 MHz; waits for q1
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while [ ! -f work/mxfast/res/q1.done ]; do sleep 20; done
R=work/mxfast/res; G="python3 work/mxfast/exp_state_mf.py"; L=$R/state_log.txt
run() { echo "== $*" >> $L; timeout 3000 $G "$@" >> $L 2>&1; }
run A ste1m_race_start.sav 8 260 $R/st_start_A8.json zig=140 kern
run M ste1m_race_start.sav 16 260 $R/st_start_M16.json zig=140 kern
run M ste1m_race_start.sav 32 260 $R/st_start_M32.json zig=140 kern
run A ste1m_race_drive.sav 8 330 $R/st_drive_A8.json hold kern
run M ste1m_race_drive.sav 16 330 $R/st_drive_M16.json hold kern
run M ste1m_race_drive.sav 32 330 $R/st_drive_M32.json hold kern
run A ste1m_race_up.sav 8 260 $R/st_up_A8.json zig=470 kern
run M ste1m_race_up.sav 16 260 $R/st_up_M16.json zig=470 kern
run M ste1m_race_up.sav 32 260 $R/st_up_M32.json zig=470 kern
echo ALLDONE >> $L
echo DONE > $R/q2.done
