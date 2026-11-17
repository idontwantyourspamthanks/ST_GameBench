#!/bin/bash
# isolates the face-box differences: XF = the default with ta_face (pixel-identical face) instead of ta_facestat, mg extras on (16 MHz): must equal the reference PT8 everywhere
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2
while [ ! -f res/tail.done ]; do sleep 10; done
P=res/pix; L=res/pix2_log.txt
cap() { echo "== $*" >> $L; timeout 1500 python3 pixcap2.py "$@" >> $L 2>&1; }
cap XF ste1m_race_start.sav 16 200 $P/start_XF16 zig=140
cap XF ste1m_race_up.sav 16 200 $P/up_XF16 zig=470
cap XF ste1m_race_drive.sav 16 320 $P/drive_XF16 hold
for s in start up drive; do echo "-- ${s}_PT8:${s}_XF16" >> $L; python3 pixcmp2.py $P/${s}_PT8 $P/${s}_XF16 >> $L 2>&1; done
touch res/pix2.done
# menu / mouse exploration (ta_nomouse): stock vs the final default build, same walk
timeout 900 python3 menus.py originals/MOONSHR stock > res/menus_stock.txt 2>&1
timeout 900 python3 menus.py build/mfin_hd final > res/menus_final.txt 2>&1
touch res/menus.done
# floppy cold boots + >= 2-minute steered drives (run again after the floppy_fin.py peekb fix)
R=res
for c in "ste 1024 1.62" "megaste 4096 2.06"; do
  set -- $c
  echo "=== FLOPPY $c"; timeout 1500 python3 floppy_fin.py ../../build/mfin_floppy/disk_a.st ../../build/mfin_floppy/disk_b.st $1 $2 $3 fin_$1_$2 2>&1 | cut -c1-400
done > $R/cold_floppy2.txt 2>&1
touch res/floppy2.done
./run_pix3.sh
