#!/bin/bash
export HOME=/tmp/nr12/home PYTHONUNBUFFERED=1 PYTHONPATH=/tmp/nr12/sc
while false; do sleep 20; done
cd /tmp/nr12/fl/s
G=/tmp/nr12/s/fl/NEBULUS_floppy/Nebulus_game_disk.st; C=/tmp/nr12/s/fl/NEBULUS_floppy/Nebulus_campaign_disk.st; O=/tmp/nr12/fl/out; W=/tmp/nr12/wd; REF=/tmp/nr12/x/r/base8_ste
step(){ echo "== $1 $(date +%T)" >> $O/steps.txt; }
for M in ste megaste; do
 step fl_ui_$M; python3 fl_ui.py $G $W/fui_$M $REF $M > $O/fl_ui_$M.txt 2>&1
 step rt_$M; python3 rt.py $G $W/frt_$M $C $M > $O/rt_$M.txt 2>&1
 if [ $M = ste ]; then FZ=; else FZ=skipfuzz; fi
 step f161_$M; python3 f161_nfe.py $G $W/f161_$M $M $FZ > $O/f161_$M.txt 2>&1
 step fge2_$M; python3 fge2.py $G $W/fge2_$M $M > $O/fge2_$M.txt 2>&1
 step fl_ui16_$M; CPU16=1 python3 fl_ui.py $G $W/fui16_$M $REF $M > $O/fl_ui16_$M.txt 2>&1
 step rt16_$M; CPU16=1 python3 rt.py $G $W/frt16_$M $C $M > $O/rt16_$M.txt 2>&1
done
echo done > $O/done
