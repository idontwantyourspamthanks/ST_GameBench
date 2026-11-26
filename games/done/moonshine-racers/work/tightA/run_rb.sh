#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tightA
while ! grep -q DONE5 res/cyc3.log 2>/dev/null; do sleep 15; done
B=hd_clouds,hd_nomap,hd_nomap2,hd_stage,mr_edge,rd_draw,rd_geom,rd_init,mt_clock,mt_pre,mx_pre,mx_sync
python3 rb_trace.py race_start $B,hd_init res/rb_ref.txt 80
python3 rb_trace.py race_start $B,ta_init,ta_erase,ta_rb res/rb_rb.txt 80
python3 rb_trace.py race_start $B,ta_init,ta_erase,ta_rb,ta_rb0 res/rb_rb0.txt 80
echo DONE6
