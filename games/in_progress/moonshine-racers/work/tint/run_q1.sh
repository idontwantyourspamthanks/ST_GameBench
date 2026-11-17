#!/bin/bash
# queue 1: pixel gates, masked pixel gate (+ negative controls), cycles
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
while pgrep -f run_state.sh >/dev/null; do sleep 10; done
T=work/tint; R=$T/res
python3 $T/pix_int.py race_start:10 race_start:55 race_start:90 race_start:100 race_start:150 race_grid:10 race_grid:120 race_grid:150 race_up:10 race_up:40 race_up:90 race_up:150 race_drive:10 race_drive:40 race_drive:90 race_drive:150 > $R/pix_ctl.txt 2>&1
F="hd_stage ta_init ta_erase ta_face ta_glyph ta_ymw hd_clouds hd_nomap hd_nomap2 mr_edge rd_geom rd_draw rd_init tb_car tb_carph tc_clr tc_dist tc_hit1 tc_hit2 tc_ord tc_proj"
C="--cand $F --ref test_hdref hd_clouds mr_edge rd_geom rd_draw rd_init --stock mr_edge rd_geom rd_draw rd_init --out work/tint/mask"
python3 tools/msrmask.py $C --snapshots race_start race_grid race_up race_drive --flips 10 40 90 > $R/mask_final.txt 2>&1
python3 tools/msrmask.py $C --snapshots race_start --flips 10 --neg nopaint > $R/mask_neg_nopaint.txt 2>&1
python3 tools/msrmask.py $C --snapshots race_start --flips 10 --neg nowipe > $R/mask_neg_nowipe.txt 2>&1
echo DONE_Q1 > $R/q1.done
