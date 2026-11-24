#!/bin/bash
# T (default set, tick ON, no extras) references for the kernel-area compare; waits for q4
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while [ ! -f work/mxfast/res/q4.done ]; do sleep 20; done
R=work/mxfast/res; G="python3 work/mxfast/exp_state_mf.py"; L=$R/state_log_T.txt
run() { echo "== $*" >> $L; timeout 3000 $G "$@" >> $L 2>&1; }
run T ste1m_race_start.sav 8 260 $R/st_start_T8.json zig=140 kern
run T ste1m_race_drive.sav 8 330 $R/st_drive_T8.json hold kern
run T ste1m_race_up.sav 8 260 $R/st_up_T8.json zig=470 kern
echo DONE > $R/q5.done
