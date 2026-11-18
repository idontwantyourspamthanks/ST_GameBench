#!/bin/bash
# same-clock comparisons (is the drive-scene message-cell difference a clock effect, or the extras?): reference at 16 MHz (PT16 = previous default, mt_sync) vs
# X16 (final default, mg extras) vs P16 (previous default with the old mx extras); renders must match within the face box
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2
while [ ! -f res/floppy2.done ]; do sleep 10; done
P=res/pix; L=res/pix3_log.txt
cap() { echo "== $*" >> $L; timeout 1500 python3 pixcap2.py "$@" >> $L 2>&1; }
cap PT ste1m_race_drive.sav 16 320 $P/drive_PT16 hold
cap PT ste1m_race_start.sav 16 200 $P/start_PT16 zig=140
for s in drive_PT16:drive_X16 drive_PT16:drive_P16 drive_P16:drive_X16 drive_PT16:drive_XM16 start_PT16:start_X16 start_PT16:start_XF16; do
  echo "-- $s" >> $L; python3 pixcmp2.py $P/${s%%:*} $P/${s##*:} >> $L 2>&1
done
touch res/pix3.done
