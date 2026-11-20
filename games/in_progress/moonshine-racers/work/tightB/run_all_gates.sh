#!/bin/sh
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers
export MSRPATCH_TOOL=$PWD/work/tightB/msrpatch_priv.py MSR_LIVETAG=_tb
R=work/tightB/res
T="python3 work/tightB/tbab.py"
B="tb_blit tb_blit11 tb_blit13 tb_blit15"
$T --extra $B                                                > $R/pix_blit_final.txt 2>&1
$T --extra tb_car tb_carph $B                                > $R/pix_both.txt 2>&1
$T --extra $B --poke b46cc=0006 --tag negblit                > $R/pix_blit_NEG_planes.txt 2>&1
$T --extra tbb_h tbb_h11 tbb_h13 tbb_h15                     > $R/pix_blit_hog.txt 2>&1
# state: tick (T) and tick+extras (X), car+blit together
PB=tb_car+tb_carph+tb_blit+tb_blit11+tb_blit13+tb_blit15
run() { python3 work/tightB/exp_state_tb.py "$@"; }
for scene in start:200 drive:270; do
  s=${scene%%:*}; n=${scene##*:}; snap=ste1m_race_$s.sav
  run T+$PB $snap 8 $n $R/both_${s}_T8_tb.json
  for mhz in 8 16 32; do run X+$PB $snap $mhz $n $R/both_${s}_X${mhz}_tb.json; done
done
echo DONE > $R/run_all.done
