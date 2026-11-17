#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while [ ! -f work/mxfast/res/q7.done ]; do sleep 20; done
R=work/mxfast/res; M=work/mxfast
for b in mg mf; do
  for c in "ste 1024 1.62 16" "megaste 4096 2.06 16"; do
    set -- $c
    echo "=== FLOPPY gate $b $c"; timeout 1500 python3 tools/msrfloppy.py gate $M/build/${b}_fl/disk_a.st --disk-b $M/build/${b}_fl/disk_b.st --machine $1 --mem $2 --tos $3 --cpu $4 --name mxf2_${b}_$1 2>&1 | cut -c1-300
  done
done > $R/floppy3.txt 2>&1
echo DONE > $R/q9.done
