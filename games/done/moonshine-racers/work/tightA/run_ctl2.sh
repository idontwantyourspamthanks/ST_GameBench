#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tightA
python3 pix_ctl.py race_start:10 race_start:55 race_start:90 race_start:100 race_start:150 race_grid:10 race_grid:120 race_grid:150 race_up:10 race_up:40 race_up:90 race_up:150 race_drive:10 race_drive:40 race_drive:90 race_drive:150 > res/ctl_run2.txt 2>&1
B=hd_clouds,hd_nomap,hd_nomap2,hd_stage,mr_edge,rd_draw,rd_geom,rd_init,mt_clock,mt_pre,mx_pre,mx_sync
python3 rb_trace.py race_start $B,ta_init,ta_erase,ta_rb poke=be7aa=4e71 res/rb_rbneg.txt 80 > res/rbneg.log 2>&1
echo DONE9 >> res/rbneg.log
