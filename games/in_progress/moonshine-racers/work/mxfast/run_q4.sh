#!/bin/bash
# cold boots + 2-minute drives of the mf / mg builds; waits for q3
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while [ ! -f work/mxfast/res/q3.done ]; do sleep 20; done
python3 work/mxfast/mkbuild.py > work/mxfast/res/mkbuild.txt 2>&1
R=work/mxfast/res; T=work/tint
for b in mf_hd mg_hd; do
for c in "ste 1024 1.62 0,16" "ste 4096 1.62 0,16" "megaste 1024 2.06 0,16"; do
  set -- $c
  echo "=== HD cold $b $c"; timeout 1500 python3 $T/cold_int.py $1 $2 $3 work/mxfast/build/$b mxf_${b}_$1_$2 $4 2>&1 | grep -v "^$" | cut -c1-520
done
done > $R/cold_hd.txt 2>&1
for b in mf_hd mg_hd; do
  for mhz in 8 16; do
    echo "=== play 2 min $b $mhz MHz"; timeout 900 python3 $T/play5_int.py ste 1024 1.62 work/mxfast/build/$b $mhz 6000 2>&1 | tail -25
  done
done > $R/play2.txt 2>&1
echo DONE > $R/q4.done
