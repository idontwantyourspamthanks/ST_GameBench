#!/bin/bash
# which patch makes the grid (standing start, 8 MHz, no extras) main frames differ from the previous default PT (one glyph cell missing in some frames)?
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2
P=res/pix; L=res/bisect_log.txt
cap() { echo "== $*" >> $L; timeout 1500 python3 pixcap2.py "$@" >> $L 2>&1; }
cap PT ste1m_race_grid.sav 8 120 $P/grid_PT8_rep
cap T ste1m_race_grid.sav 8 120 $P/grid_T8
cap XF ste1m_race_grid.sav 8 120 $P/grid_XF8
TINT_DROP=ta_rb,ta_rb0 cap X ste1m_race_grid.sav 8 120 $P/grid_Xnrb8
TINT_DROP=ta_nomouse cap X ste1m_race_grid.sav 8 120 $P/grid_Xnnm8
TINT_DROP=tb_blit,tb_blit11,tb_blit13,tb_blit15 cap X ste1m_race_grid.sav 8 120 $P/grid_Xnblit8
for v in PT8_rep T8 XF8 Xnrb8 Xnnm8 Xnblit8; do echo "-- grid_PT8:grid_$v" >> $L; python3 pixcmp2.py $P/grid_PT8 $P/grid_$v >> $L 2>&1; done
# is the glyph-cell difference of the drive scene at 16 MHz (time-out messages) new with mg, or a property of the extras of the previous default too?
cap P ste1m_race_drive.sav 16 320 $P/drive_P16 hold
cap XM ste1m_race_drive.sav 16 320 $P/drive_XM16 hold
for v in P16 XM16; do echo "-- drive_PT8:drive_$v" >> $L; python3 pixcmp2.py $P/drive_PT8 $P/drive_$v >> $L 2>&1; done
touch res/bisect.done
