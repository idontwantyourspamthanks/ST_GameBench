#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tightA
while ! grep -q DONE4 res/cold.log 2>/dev/null; do sleep 15; done
for sc in race_start race_grid; do
 for v in ta_rb+ta_rb0 ta_init+ta_erase+ta_face+ta_glyph+ta_rb+ta_rb0+ta_ymw+ta_nomouse; do
  n=$(echo $v | tr '+' '_'); python3 cyc.py $sc $v 230 res/cyc_${sc}_$n.json 2>&1 | grep -E "mean"
 done
done
echo DONE5
