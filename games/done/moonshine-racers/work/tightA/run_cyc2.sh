#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tightA
while ! grep -q DONE res/state_all.log; do sleep 10; done
for sc in race_start race_grid; do
 for v in base ta_init+ta_erase+ta_face+ta_glyph+ta_rb+ta_ymw+ta_nomouse ta_init+ta_erase+ta_facestat+ta_glyph+ta_rb+ta_ymw+ta_nomouse ta_rb ta_ymw ta_nomouse; do
  n=$(echo $v | tr '+' '_'); python3 cyc.py $sc $v 230 res/cyc_${sc}_$n.json 2>&1 | grep -E "mean"
 done
done
echo DONE2
