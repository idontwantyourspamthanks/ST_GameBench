#!/bin/bash
# re-gate the floppy release after fl_driveb (default yes): the ONE-DRIVE swap route must still work, so gate a LONE disk A (no sibling disk_b next to it, else
# Hatari's bAutoInsertDiskB puts disk 2 in drive B) with --disk-b pointing at the real disk B for the swap.
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
L=work/tint2/res/two_log.txt
rm -rf /tmp/loneA; mkdir -p /tmp/loneA
cp build/mfin_floppy/disk_a.st /tmp/loneA/disk_a.st
ls /tmp/loneA
for c in "ste 1024 1.62 16" "megaste 4096 2.06 16"; do
  set -- $c
  echo "=== LONE-A gate $c" >> $L
  timeout 900 python3 tools/msrfloppy.py gate /tmp/loneA/disk_a.st --disk-b build/mfin_floppy/disk_b.st --machine $1 --mem $2 --tos $3 --cpu $4 --name two_$1_$2 2>&1 | cut -c1-320 >> $L
done
echo "=== bus errors, rebuilt default floppy" >> $L
timeout 900 python3 work/tint2/bus.py build/mfin_floppy/disk_a.st build/mfin_floppy/disk_b.st ste 1024 1.62 v1b >> $L 2>&1
echo ALLDONE >> $L; touch work/tint2/res/two.done
