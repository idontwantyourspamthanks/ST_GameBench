#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tightA
CR=hd_clouds,hd_nomap,hd_nomap2,hd_stage,mr_edge,rd_draw,rd_geom,rd_init,mt_clock,mt_pre,mx_pre,mx_sync
for v in ta_init,ta_erase ta_init,ta_erase,ta_face,ta_glyph ta_ymw ta_rb ta_nomouse; do
  echo "== $v"; python3 exp_state_ta.py race_drive $CR,$v 130 res/state/bis_$v.json hold 2>&1 | tail -2
done
echo DONEB
