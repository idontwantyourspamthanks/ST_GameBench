#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while [ ! -f work/tint/res/q7.done ]; do sleep 10; done
unset TINT_SHOW
R=work/tint/res
for sc in race_start race_up; do
  for v in X NX; do python3 work/tint/steer_int.py $sc $v 8 700 $R/ext8_${sc}_$v.json steer=zig mode=pass >> $R/ext8_log.txt 2>&1; done
done
echo DONE_Q8 > $R/q8.done
