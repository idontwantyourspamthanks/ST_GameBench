#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
export MSRPATCH_TOOL=$PWD/work/tightB/msrpatch_priv.py MSR_LIVETAG=_tb
R=work/tightB/res
python3 work/tightB/tbab.py --extra tb_blit tb_blit11 tb_blit13 tb_blit15 --poke b46d2=0006 --tag negblit2 > $R/pix_blit_NEG_planes.txt 2>&1
python3 work/tightB/carcost.py race_start 400 tb_car tb_carph > $R/carcost_start.txt 2>&1
python3 work/tightB/carcost.py race_drive 400 tb_car tb_carph > $R/carcost_drive.txt 2>&1
for v in base+tb_blit+tb_blit11+tb_blit13+tb_blit15 base+tbb_h+tbb_h11+tbb_h13+tbb_h15; do python3 work/tightB/isrlat.py race_start $v 1500 $R/isr2_$v.json >> $R/isr2.txt 2>&1; done
python3 work/tightB/tb_drive.py work/tightB/build/hd_tb ste 1024 > $R/drive_ste1m.txt 2>&1
python3 work/tightB/tb_drive.py work/tightB/build/hd_tb ste 4096 > $R/drive_ste4m.txt 2>&1
echo DONE > $R/run_final.done
