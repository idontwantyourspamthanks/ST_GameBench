#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
R=work/triple/res
while [ ! -f $R/lat2.done ]; do sleep 5; done
python3 work/triple/meas2.py race_drive work/triple/live/X 16 1300 $R/lat3_X16.json > $R/lat3_X16.out 2>&1
python3 work/triple/meas2.py race_drive work/triple/live/X 16 1300 $R/lat3_NW16.json poke=b8206=6008 poke=b8634=4e71 > $R/lat3_NW16.out 2>&1
echo DONE > $R/lat3.done
