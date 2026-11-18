#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
R=work/mxfast/res
S="python3 work/mxfast/steer_mf.py race_drive"
$S M 8 1300 $R/ext_M8_s0.json steer=zig mode=pass >> $R/q1.log 2>&1
$S M 8 1300 $R/ext_M8_sm3.json steer=zig mode=pass poke=b8f6c=fffd >> $R/q1.log 2>&1
$S M 8 1300 $R/ext_M8_sm6.json steer=zig mode=pass poke=b8f6c=fffa >> $R/q1.log 2>&1
$S M 8 1300 $R/ext_M8_sm9.json steer=zig mode=pass poke=b8f6c=fff7 >> $R/q1.log 2>&1
echo DONE > $R/q1.done
