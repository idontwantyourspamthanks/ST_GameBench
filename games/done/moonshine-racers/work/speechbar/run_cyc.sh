#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
R=work/speechbar/res; L=$R/cyc_log.txt
for scene in race_start race_grid; do
  for set in F S; do
    echo "== $set $scene" >> $L
    timeout 1500 python3 work/speechbar/cyc_sb.py $scene $set 8 230 $R/cyc_${scene}_$set.json steer=none mode=cyc >> $L 2>&1
  done
done
echo DONE >> $L
