#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while [ ! -f work/mxfast/res/q5.done ]; do sleep 20; done
R=work/mxfast/res; S="python3 work/mxfast/steer_mf.py race_drive"
$S G 8 1300 $R/ext_G8_sp3.json steer=zig mode=pass poke=b8f6c=0003 >> $R/q6.log 2>&1
$S G 8 1300 $R/ext_G8_sp6.json steer=zig mode=pass poke=b8f6c=0006 >> $R/q6.log 2>&1
$S G 16 1300 $R/ext_G16_s0.json steer=zig mode=pass >> $R/q6.log 2>&1
$S M 16 1300 $R/ext_M16_s0.json steer=zig mode=pass >> $R/q6.log 2>&1
$S X 16 1300 $R/ext_X_16.json steer=zig mode=pass >> $R/q6.log 2>&1
echo DONE > $R/q6.done
