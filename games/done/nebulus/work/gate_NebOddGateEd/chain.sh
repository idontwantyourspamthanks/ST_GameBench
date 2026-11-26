#!/bin/bash
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor; B=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebOddGateEd/build; L=/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebOddGateEd/logs; mkdir -p $L; S=/tmp/ne/oge
r(){ n=$1; shift; echo "START $n $(date +%T)" >> $L/chain.out; timeout 5400 "$@" > $L/$n.log 2>&1; echo "END $n rc=$? $(date +%T)" >> $L/chain.out; }
for m in ste megaste st; do
 r e180_looks_odd2_$m python3 e180.py $B /tmp/ne/oge_w_$m $m /tmp/ne/odd/looks.ovl /tmp/ne/odd/odd2.ovl --quick --snap /tmp/ne/oge_snap_$m.sav
done
for m in ste megaste; do r e180_stress_$m python3 e180.py $B /tmp/ne/oge_ws_$m $m /tmp/ne/odd/stress*.ovl --quick --snap /tmp/ne/oge_snap_$m.sav; done
r e180_flow_ste python3 e180.py $B /tmp/ne/oge_wf ste --flow --snap /tmp/ne/oge_snap_ste.sav
r e180_flags_ste python3 e180.py $B /tmp/ne/oge_wg ste --flags --snap /tmp/ne/oge_snap_ste.sav
for m in ste megaste; do r e180_disk_$m python3 e180.py $B /tmp/ne/oge_wd_$m $m /tmp/ne/odd/odd2.ovl /tmp/ne/odd/looks.ovl --disk --quick --snap /tmp/ne/oge_snap_$m.sav; done
for m in ste megaste; do r e161_$m python3 e161.py $B /tmp/ne/oge_w161_$m $m; done
r e91 python3 /home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/gate_NebOddGateEd/e91_oge.py
for m in ste megaste st; do for e in e150 e140 e170; do r ${e}_$m python3 $e.py $B /tmp/ne/oge_w${e}_$m $m; done; done
echo ALLDONE >> $L/chain.out
