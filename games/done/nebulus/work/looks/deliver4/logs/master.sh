#!/bin/bash
# NebConveyor gate chain: one Hatari at a time, fresh snapshots per build and machine (made by the gates from $B, signature-checked)
cd /tmp/nlcv/games/in_progress/nebulus; X=/tmp/nlcv/x; L=$X/logs; B=$X/b_new; NE=$X/lg/ne/odd; S=work/editor
export PYTHONUNBUFFERED=1 HOME=/tmp/nlcv/home
SIGN=10307e3010ffff0002080c7e0c08ffff0002; SIGO=$(printf 'Door + opposite' | xxd -p); NOS=$(printf 'Conveyor left' | xxd -p)
export SNAP_EXPECT=$SIGN
run(){ n=$1; shift; "$@" > $L/$n.log 2>&1; echo "$(date +%T) $n done rc=$?" >> $L/master.progress; }
steps="$*"
for st in $steps; do case $st in
 e208_*) m=${st#e208_}; run e208_$m python3 $S/e208.py $B $X/user/e208_$m $m;;
 ab) run ab_old env SIG=$SIGO NOSIG=$NOS python3 $S/e208_ab.py run $X/b_old $X/title_ste_old.sav $X/ab/old ste
     run ab_new env SIG=$SIGN python3 $S/e208_ab.py run $B $X/title_ste_new.sav $X/ab/new ste
     run ab_cmp python3 $S/e208_ab.py cmp $X/ab/old $X/ab/new;;
 e200_*) m=${st#e200_}; run e200_$m python3 $S/e200.py $B $X/user/e200_$m $m;;
 e201_*) m=${st#e201_}; run e201_$m python3 $S/e201.py $B $X/user/e201_$m $m;;
 e203_*) m=${st#e203_}; run e203_$m python3 $S/e203.py $B $X/user/e203_$m $m;;
 e150_*) m=${st#e150_}; run e150_$m python3 $S/e150.py $B $X/wd150_$m $m;;
 e170_*) m=${st#e170_}; run e170_$m python3 $S/e170.py $B $X/wd170_$m $m;;
 e180q_ste) run e180q_ste python3 $S/e180.py $B $X/wd180q_ste ste $NE/odd2.ovl $NE/stress01.ovl $NE/stress05.ovl --quick --snap $X/title_ste_new.sav;;
 e180q_megaste) run e180q_megaste python3 $S/e180.py $B $X/wd180q_megaste megaste $NE/odd2.ovl $NE/stress05.ovl --quick --snap $X/title_megaste_new.sav;;
 fl_ui_*) m=${st#fl_ui_}; run fl_ui_$m python3 work/floppy/fl_ui.py $X/fl_game.st $X/wdflui_$m $X/lg/r/base8_ste $m;;
 esac; done
echo "$(date +%T) chain [$steps] finished" >> $L/master.progress
