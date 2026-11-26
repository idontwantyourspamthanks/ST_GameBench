#!/bin/sh
# usage: run_state.sh TAG "CANDIDATE EXTRA PATCHES (comma)" 
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/tightA
TAG=$1; EXTRA=$2
R=hd_clouds,hd_init,hd_nomap,hd_nomap2,hd_stage,mr_edge,rd_draw,rd_geom,rd_init
T=mt_clock,mt_pre,mx_pre,mx_sync
CR=hd_clouds,hd_nomap,hd_nomap2,hd_stage,mr_edge,rd_draw,rd_geom,rd_init
mkdir -p res/state
for tick in on off; do
  if [ $tick = on ]; then RS="$R,$T"; CS="$CR,$EXTRA,$T"; else RS="$R"; CS="$CR,$EXTRA"; fi
  [ -f res/state/${TAG}_R_start_$tick.json ] || python3 exp_state_ta.py race_start $RS 200 res/state/${TAG}_R_start_$tick.json hold
  [ -f res/state/${TAG}_C_start_$tick.json ] || python3 exp_state_ta.py race_start $CS 200 res/state/${TAG}_C_start_$tick.json hold
  [ -f res/state/${TAG}_R_drive_$tick.json ] || python3 exp_state_ta.py race_drive $RS 280 res/state/${TAG}_R_drive_$tick.json hold
  [ -f res/state/${TAG}_C_drive_$tick.json ] || python3 exp_state_ta.py race_drive $CS 280 res/state/${TAG}_C_drive_$tick.json hold
done
for mhz in 16 32; do
  [ -f res/state/${TAG}_R_start_x$mhz.json ] || python3 exp_state_ta.py race_start $R,$T 200 res/state/${TAG}_R_start_x$mhz.json hold mhz=$mhz
  [ -f res/state/${TAG}_C_start_x$mhz.json ] || python3 exp_state_ta.py race_start $CR,$EXTRA,$T 200 res/state/${TAG}_C_start_x$mhz.json hold mhz=$mhz
done
echo DONE
