#!/bin/bash
# after the measurements: (1) screen writes after $7b52 ? (main frame at the flip vs at $7b52), then cold boots, tail runs, face isolation
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tint2
while [ ! -f res/meas.done ]; do sleep 10; done
P=res/pix; L=res/diag_log.txt
cap() { echo "== $*" >> $L; timeout 1500 python3 pixcap2.py "$@" >> $L 2>&1; }
cap PT ste1m_race_grid.sav 8 120 $P/grid_PT8_b52 at=7b52
cap X ste1m_race_grid.sav 8 120 $P/grid_X8_b52 at=7b52
cap PT ste1m_race_drive.sav 8 320 $P/drive_PT8_b52 hold at=7b52
cap X ste1m_race_drive.sav 16 320 $P/drive_X16_b52 hold at=7b52
for p in grid_PT8:grid_PT8_b52 grid_PT8_b52:grid_X8_b52 grid_PT8_b52:grid_X8 drive_PT8:drive_PT8_b52 drive_PT8_b52:drive_X16_b52 drive_PT8_b52:drive_X16; do
  echo "-- $p" >> $L; python3 pixcmp2.py $P/${p%%:*} $P/${p##*:} >> $L 2>&1
done
touch res/diag.done
./run_cold.sh
./run_tail.sh
./run_pix2.sh
