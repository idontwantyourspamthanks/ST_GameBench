#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tightA
while ! grep -q DONE2 res/cyc2.log; do sleep 10; done
B=hd_clouds,hd_nomap,hd_nomap2,hd_stage,mr_edge,rd_draw,rd_geom,rd_init
python3 joy_test.py $B,hd_init
python3 joy_test.py $B,ta_init,ta_erase,ta_nomouse
echo DONE3
