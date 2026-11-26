#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus; L=work/gate_NebRelease12/logs; B=/tmp/r12; R=$B/r; HD=$B/s/hd/NEBULUS; O=/tmp/looksgate/ne/odd; export PYTHONUNBUFFERED=1
rl(){ python3 work/looks/run_look.py "$@"; }
step(){ echo "== $1 $(date +%T)" >> $L/p2a_steps.txt; }
for M in ste megaste st; do
 step e170_$M; python3 work/editor/e170.py $HD $B/wd170_$M $M > $L/hd_e170_$M.log 2>&1
 step base8_$M; rl $B/hd_base8 $R/base8_$M 8 camp $M > $L/hd_base8_$M.log 2>&1
 if [ $M = st ]; then
  step st6; rl $B/hd_st6 $R/st6_st 6 camp st > $L/hd_st6_st.log 2>&1; python3 work/looks/check_look.py $R/base8_st $R/st6_st st6 > $L/hd_check_st.txt 2>&1
 else
  step looks15_$M; rl $B/hd_looks15 $R/looks15_$M 15 camp $M > $L/hd_looks15_$M.log 2>&1; python3 work/looks/check_look.py $R/base8_$M $R/looks15_$M looks15 > $L/hd_check_$M.txt 2>&1
 fi
 step e190_$M; REFDIR=$R/base8_$M python3 work/editor/e190.py $HD $B/wd190_$M $M > $L/hd_e190_$M.log 2>&1
 step e180disk_$M; python3 work/editor/e180.py $HD $B/wd180d_$M $M $O/odd2.ovl $O/looks.ovl --disk > $L/hd_e180_disk_$M.log 2>&1
 step e180all12_$M; python3 work/editor/e180.py $HD $B/wd180a_$M $M $O/all12.ovl --quick > $L/hd_e180_all12_$M.log 2>&1
done
echo done > $L/p2a.done
