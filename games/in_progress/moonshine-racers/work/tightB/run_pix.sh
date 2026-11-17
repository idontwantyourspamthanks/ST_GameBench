#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
export MSRPATCH_TOOL=$PWD/work/tightB/msrpatch_priv.py MSR_LIVETAG=_tb
R=work/tightB/res
T="python3 work/tightB/tbab.py"
B="tb_blit tb_blit11 tb_blit13 tb_blit15"
$T --extra $B                                                > $R/pix_blit_final.txt 2>&1
$T --extra tbb_h tbb_h11 tbb_h13 tbb_h15                     > $R/pix_blit_hog.txt 2>&1
$T --extra $B --poke b46cc=0006 --tag negblit                > $R/pix_blit_NEG_planes.txt 2>&1
$T --extra tb_car tb_carph $B                                > $R/pix_both.txt 2>&1
echo DONE > $R/run_pix.done
