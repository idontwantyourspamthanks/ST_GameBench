#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while pgrep -f "work/tint/cold_int.py" > /dev/null; do sleep 15; done
R=work/mxfast/res; T=work/tint
for c in "ste 4096 1.62 0,16" "megaste 1024 2.06 0,16"; do
  set -- $c
  echo "=== HD cold mg_hd $c"; timeout 1500 python3 $T/cold_int.py $1 $2 $3 work/mxfast/build/mg_hd mxf_mg_hd_$1_$2 $4 2>&1 | grep -v "^$" | cut -c1-520
done >> $R/cold_hd.txt 2>&1
for b in mf_hd mg_hd; do
  echo "=== play 2 min $b 8 MHz"; timeout 900 python3 $T/play5_int.py ste 1024 1.62 work/mxfast/build/$b 8 6000 2>&1 | tail -25
done > $R/play2.txt 2>&1
echo DONE > $R/q4.done
