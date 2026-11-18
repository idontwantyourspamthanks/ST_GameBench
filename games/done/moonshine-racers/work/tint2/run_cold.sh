#!/bin/bash
# Cold boots of the final default build: HD (STE 1 MB, STE 4 MB, Mega STE 1 MB at 8 then 16 MHz) and floppy (STE 1 MB, Mega STE 4 MB), each with a >= 2-minute drive
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while [ ! -f work/tint2/res/meas.done ]; do sleep 10; done
R=work/tint2/res
python3 tools/msrpatch.py build --out build/mfin_hd > $R/build_hd.txt 2>&1
python3 tools/msrpatch.py build --floppy --out build/mfin_floppy > $R/build_floppy.txt 2>&1
for c in "ste 1024 1.62 0,16" "ste 4096 1.62 0,16" "megaste 1024 2.06 0,16"; do
  set -- $c
  echo "=== HD cold $c"; timeout 1500 python3 work/tint2/cold_fin.py $1 $2 $3 build/mfin_hd fin_$1_$2 $4 2>&1 | grep -v "^$" | cut -c1-560
done > $R/cold_hd.txt 2>&1
for c in "ste 1024 1.62" "megaste 4096 2.06"; do
  set -- $c
  echo "=== FLOPPY $c"; timeout 1500 python3 work/tint2/floppy_fin.py build/mfin_floppy/disk_a.st build/mfin_floppy/disk_b.st $1 $2 $3 fin_$1_$2 2>&1 | cut -c1-400
done > $R/cold_floppy.txt 2>&1
touch $R/cold.done
