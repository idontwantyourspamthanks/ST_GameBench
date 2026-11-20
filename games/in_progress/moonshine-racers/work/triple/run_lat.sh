#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
R=work/triple/res
python3 work/triple/meas2.py race_drive work/triple/live/X 8 1300 $R/lat2_X8.json > $R/lat2_X8.out 2>&1
rm -rf $(ls -dt /tmp/strun-* | head -0)
python3 work/triple/meas2.py race_drive work/triple/live/X 8 1300 $R/lat2_NW8.json poke=b8206=6008 poke=b8634=4e71 > $R/lat2_NW8.out 2>&1
echo DONE > $R/lat2.done
