#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tightA
while ! grep -q DONE7 res/prof.log 2>/dev/null; do sleep 15; done
python3 pix_hatari.py race_start,race_grid,race_up,race_drive 10,40,90,150 main > res/pix_hatari.txt 2>&1
python3 pix_hatari.py race_start 90 neg neg > res/pix_hatari_neg.txt 2>&1
echo DONE8 >> res/pix_hatari.txt
