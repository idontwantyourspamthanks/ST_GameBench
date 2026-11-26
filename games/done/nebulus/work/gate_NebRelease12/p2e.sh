#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus; L=work/gate_NebRelease12/logs; B=/tmp/r12; R=$B/r; HD=$B/s/hd/NEBULUS; O=/tmp/looksgate/ne/odd; export PYTHONUNBUFFERED=1 SNAP_EXPECT=303900077cbe
step(){ echo "== $1 $(date +%T)" >> $L/p2e_steps.txt; }
for M in ste megaste st; do S="--snap $B/snap/title_$M.sav"
 step e180disk_$M; python3 work/editor/e180.py $HD $B/w2_180d_$M $M $O/odd2.ovl $O/looks.ovl --disk $S > $L/hd_e180_disk_$M.log 2>&1
 step e180all12_$M; python3 work/editor/e180.py $HD $B/w2_180a_$M $M $O/all12.ovl --quick $S > $L/hd_e180_all12_$M.log 2>&1
 step e190_$M; REFDIR=$R/base8_$M python3 work/editor/e190.py $HD $B/w2_190_$M $M $S > $L/hd_e190_$M.log 2>&1
done
echo done > $L/p2e.done
