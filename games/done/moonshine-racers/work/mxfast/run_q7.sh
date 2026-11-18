#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while [ ! -f work/mxfast/res/q6.done ]; do sleep 20; done
R=work/mxfast/res; M=work/mxfast
for v in X M G; do timeout 1500 python3 $M/hflips.py $v 16 165 $R/hf_${v}16 >> $R/q7.log 2>&1; done
for c in M G; do python3 $M/hflips_cmp.py $R/hf_X16 $R/hf_${c}16 >> $R/hflips_cmp.txt 2>&1; done
echo HF > $R/q7.hf
for b in mg; do
  for c in "ste 1024 1.62 16" "megaste 4096 2.06 16"; do
    set -- $c
    echo "=== FLOPPY gate $b $c"; timeout 1500 python3 tools/msrfloppy.py gate $M/build/${b}_fl/disk_a.st --disk-b $M/build/${b}_fl/disk_b.st --machine $1 --mem $2 --tos $3 --cpu $4 --name mxf_${b}_$1 2>&1 | cut -c1-300
  done
done > $R/floppy.txt 2>&1
echo FL > $R/q7.fl
for b in mg_hd; do
  echo "=== HD cold $b megaste 4096"; timeout 1500 python3 work/tint/cold_int.py megaste 4096 2.06 $M/build/$b mxf_${b}_megaste4m 0,16 2>&1 | grep -v "^$" | cut -c1-400
done > $R/cold_megaste4m.txt 2>&1
echo DONE > $R/q7.done
