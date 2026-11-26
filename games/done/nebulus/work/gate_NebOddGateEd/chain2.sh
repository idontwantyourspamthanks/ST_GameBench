#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor; B=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebOddGateEd/build; L=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebOddGateEd/logs; mkdir -p $L; S=/tmp/ne/oge
r(){ n=$1; shift; echo "START $n $(date +%T)" >> $L/chain.out; timeout 5400 "$@" > $L/$n.log 2>&1; echo "END $n rc=$? $(date +%T)" >> $L/chain.out; }
r e180_flow_ste python3 e180.py $B /tmp/ne/oge_wf ste --flow --snap /tmp/ne/oge_snap_ste.sav
r e180_flags_ste python3 e180.py $B /tmp/ne/oge_wg ste --flags --snap /tmp/ne/oge_snap_ste.sav
r e170_ste python3 e170.py $B /tmp/ne/oge_w170_ste ste
r e150_ste python3 e150.py $B /tmp/ne/oge_w150_ste ste
r e140_ste python3 e140.py $B /tmp/ne/oge_w140_ste ste
r e161_ste python3 e161.py $B /tmp/ne/oge_w161_ste ste
r e180_disk_ste python3 e180.py $B /tmp/ne/oge_wd_ste ste /tmp/ne/odd/odd2.ovl /tmp/ne/odd/looks.ovl --disk --quick --snap /tmp/ne/oge_snap_ste.sav
r e91 python3 /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebOddGateEd/e91_oge.py
for m in megaste st; do for e in e170 e150 e140; do r ${e}_$m python3 $e.py $B /tmp/ne/oge_w${e}_$m $m; done; done
r e161_megaste python3 e161.py $B /tmp/ne/oge_w161_megaste megaste
r e180_disk_megaste python3 e180.py $B /tmp/ne/oge_wd_megaste megaste /tmp/ne/odd/odd2.ovl /tmp/ne/odd/looks.ovl --disk --quick --snap /tmp/ne/oge_snap_megaste.sav
r e180_stress_megaste python3 e180.py $B /tmp/ne/oge_ws_megaste megaste /tmp/ne/odd/stress*.ovl --quick --snap /tmp/ne/oge_snap_megaste.sav
echo ALLDONE >> $L/chain.out
