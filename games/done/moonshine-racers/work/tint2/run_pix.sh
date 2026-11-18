#!/bin/bash
# Main-frame pixel gate (first flip of each pass, pixcap2.py).  Reference PT = the previous committed default (same HUD, ta_face, mt_sync, no extras) at 8 MHz tick ON (a stock-game
# comparison is meaningless: stock has the old HUD and the clouds).  Candidate X = the integrated default (mg extras, ta_facestat, ta_rb*, ta_nomouse, tb_blit*) at 8/16/32 MHz.
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2
while [ ! -f res/state.done ]; do sleep 10; done
P=res/pix; mkdir -p $P; L=res/pix_log.txt
cap() { echo "== $*" >> $L; timeout 1500 python3 pixcap2.py "$@" >> $L 2>&1; }
cmpx() { python3 pixcmp2.py "$@" >> $L 2>&1; }
cap PT ste1m_race_start.sav 8 200 $P/start_PT8 zig=140
cap X ste1m_race_start.sav 8 200 $P/start_X8 zig=140
cap X ste1m_race_start.sav 16 200 $P/start_X16 zig=140
cap X ste1m_race_start.sav 32 200 $P/start_X32 zig=140
cap PT ste1m_race_up.sav 8 200 $P/up_PT8 zig=470
cap X ste1m_race_up.sav 8 200 $P/up_X8 zig=470
cap X ste1m_race_up.sav 16 200 $P/up_X16 zig=470
cap X ste1m_race_up.sav 32 200 $P/up_X32 zig=470
cap PT ste1m_race_drive.sav 8 320 $P/drive_PT8 hold
cap X ste1m_race_drive.sav 8 320 $P/drive_X8 hold
cap X ste1m_race_drive.sav 16 320 $P/drive_X16 hold
cap PT ste1m_race_grid.sav 8 120 $P/grid_PT8
cap X ste1m_race_grid.sav 8 120 $P/grid_X8
cap X ste1m_race_grid.sav 16 120 $P/grid_X16
# negative controls on race_start 16 MHz: a poke that breaks the message text / box restore (fires where a message is on screen)
cap X ste1m_race_start.sav 16 200 $P/start_X16_glyph zig=140 poke=be660=0002
cap X ste1m_race_start.sav 16 200 $P/start_X16_erase zig=140 poke=be042=0040
for s in start_PT8:start_X8 start_PT8:start_X16 start_PT8:start_X32 up_PT8:up_X8 up_PT8:up_X16 up_PT8:up_X32 drive_PT8:drive_X8 drive_PT8:drive_X16 grid_PT8:grid_X8 grid_PT8:grid_X16 start_PT8:start_X16_glyph start_PT8:start_X16_erase; do
  echo "-- $s" >> $L; cmpx $P/${s%%:*} $P/${s##*:}
done
echo "-- control: reference pass k vs reference pass k+1" >> $L
cmpx $P/start_PT8 $P/start_PT8 --k1
cmpx $P/up_PT8 $P/up_PT8 --k1
cmpx $P/drive_PT8 $P/drive_PT8 --k1
echo ALLDONE >> $L; touch res/pix.done
