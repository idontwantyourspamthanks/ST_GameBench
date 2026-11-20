#!/bin/bash
# Hatari: profiles (X, M, G at 8 MHz, X_TEST=1), G steered extras at 8 MHz with margins, G state gates; waits for q2
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while [ ! -f work/mxfast/res/q2.done ]; do sleep 20; done
R=work/mxfast/res; M=work/mxfast
for v in X M G; do
  timeout 900 python3 $M/prof_mx.py $v ste1m_race_drive.sav 8 150 1 $R/prof_${v}_x1.txt >> $R/q3.log 2>&1
done
S="python3 $M/steer_mf.py race_drive"
$S G 8 1300 $R/ext_G8_s0.json steer=zig mode=pass >> $R/q3.log 2>&1
$S G 8 1300 $R/ext_G8_sm3.json steer=zig mode=pass poke=b8f6c=fffd >> $R/q3.log 2>&1
$S G 8 1300 $R/ext_G8_sm6.json steer=zig mode=pass poke=b8f6c=fffa >> $R/q3.log 2>&1
G="python3 $M/exp_state_mf.py"; L=$R/state_log_G.txt
run() { echo "== $*" >> $L; timeout 3000 $G "$@" >> $L 2>&1; }
run G ste1m_race_start.sav 16 260 $R/st_start_G16.json zig=140 kern
run G ste1m_race_start.sav 32 260 $R/st_start_G32.json zig=140 kern
run G ste1m_race_drive.sav 16 330 $R/st_drive_G16.json hold kern
run G ste1m_race_drive.sav 32 330 $R/st_drive_G32.json hold kern
run G ste1m_race_up.sav 16 260 $R/st_up_G16.json zig=470 kern
run G ste1m_race_up.sav 32 260 $R/st_up_G32.json zig=470 kern
echo DONE > $R/q3.done
