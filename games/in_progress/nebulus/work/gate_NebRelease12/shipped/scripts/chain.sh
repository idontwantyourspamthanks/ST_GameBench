#!/bin/bash
# HD shipped-zip gate, one machine at a time: chain.sh MACH
M=$1; N=/tmp/nr12/nb; X=/tmp/nr12/x; L=/tmp/nr12/logs/$M; B=$X/b; HD=/tmp/nr12/s/hd/NEBULUS; W=/tmp/nr12/wd; R=$X/r
mkdir -p $L $W; cd $N; export HOME=/tmp/nr12/home PYTHONUNBUFFERED=1 SNAP_EXPECT=0203131402020202 PYTHONPATH=/tmp/nr12/sc
S="--snap $X/snap/v12_$M.sav"; O=$X/ne/odd
step(){ echo "== $1 $(date +%T)" >> $L/steps.txt; }
step snap; python3 mksnap.py $HD v12 $M > $L/snap.log 2>&1
step e170; python3 work/editor/e170.py $HD $W/e170_$M $M > $L/e170.log 2>&1
step e200; REFDIR=$R/base8_$M python3 work/editor/e200.py $HD $W/e200_$M $M $S > $L/e200.log 2>&1
step e203; python3 work/editor/e203.py $HD $W/e203_$M $M $S > $L/e203.log 2>&1
step e205; python3 work/editor/e205.py $HD $W/e205_$M $M > $L/e205.log 2>&1
step e206; python3 work/editor/e206.py $W/e206_$M $M > $L/e206.log 2>&1
step e208; python3 work/editor/e208.py $HD $W/e208_$M $M $S > $L/e208.log 2>&1
step e180; python3 work/editor/e180.py $HD $W/e180_$M $M $O/odd2.ovl --quick $S > $L/e180.log 2>&1
step base8; python3 work/looks/run_look.py $B/hd_base8 $R/base8_$M 8 camp $M > $L/base8.log 2>&1
step looks15; python3 work/looks/run_look.py $B/hd_looks15 $R/looks15_$M 15 camp $M > $L/looks15.log 2>&1; python3 work/looks/check_look.py $R/base8_$M $R/looks15_$M looks15 > $L/check_looks15.txt 2>&1
echo done > $L/done
