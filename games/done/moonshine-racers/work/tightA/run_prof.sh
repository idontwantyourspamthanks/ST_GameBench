#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tightA
while ! grep -q DONE6 res/rb.log 2>/dev/null; do sleep 15; done
B=hd_clouds,hd_nomap,hd_nomap2,hd_stage,mr_edge,rd_draw,rd_geom,rd_init,mt_clock,mt_pre,mx_pre,mx_sync
python3 isr_prof.py race_start $B,hd_init 200 /tmp/tA_prof_ref.txt
python3 isr_prof.py race_start $B,ta_init,ta_erase,ta_ymw,ta_rb,ta_rb0,ta_nomouse 200 /tmp/tA_prof_isr.txt
python3 isr_sum.py /tmp/tA_prof_ref.txt 200 > res/prof_ref.txt
python3 isr_sum.py /tmp/tA_prof_isr.txt 200 > res/prof_isr.txt
echo DONE7
