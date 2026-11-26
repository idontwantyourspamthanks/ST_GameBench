#!/bin/bash
# editor / looks gates for ONE machine: chainE.sh MACH
M=$1; N=/tmp/ng12hd/nb; X=/tmp/ng12hd/x; L=/tmp/ng12hd/logs/$M; B=$X/b; HD=/tmp/ng12hd/s/hd; W=/tmp/ng12hd/wd; R=$X/r
mkdir -p $L $W; cd $N; export HOME=/tmp/ng12hd/home PYTHONUNBUFFERED=1 SNAP_EXPECT=0203131402020202
S="--snap $X/snap/v12_$M.sav"; O=$X/ne/odd
step(){ echo "== $1 $(date +%T)" >> $L/steps.txt; }
rl(){ python3 work/looks/run_look.py "$@"; }
step base8; rl $B/hd_base8 $R/base8_$M 8 camp $M > $L/base8.log 2>&1
if [ $M = st ]; then
 step st6; rl $B/hd_st6 $R/st6_st 6 camp st > $L/st6.log 2>&1; python3 work/looks/check_look.py $R/base8_st $R/st6_st st6 > $L/check_st6.txt 2>&1
fi
step looks15; rl $B/hd_looks15 $R/looks15_$M 15 camp $M > $L/looks15.log 2>&1; python3 work/looks/check_look.py $R/base8_$M $R/looks15_$M looks15 > $L/check_looks15.txt 2>&1
export REFDIR=$R/base8_$M
step e200; python3 work/editor/e200.py $HD $W/e200_$M $M $S > $L/e200.log 2>&1
step e201; python3 work/editor/e201.py $HD $W/e201_$M $M > $L/e201.log 2>&1
step e203; python3 work/editor/e203.py $HD $W/e203_$M $M $S > $L/e203.log 2>&1
step e204; python3 work/editor/e204.py $HD $W/e204_$M $M $S > $L/e204.log 2>&1
step e205; python3 work/editor/e205.py $HD $W/e205_$M $M > $L/e205.log 2>&1
step e206; python3 work/editor/e206.py $W/e206_$M $M > $L/e206.log 2>&1
step e208; python3 work/editor/e208.py $HD $W/e208_$M $M $S > $L/e208.log 2>&1
step e150; python3 work/editor/e150.py $HD $W/e150_$M $M > $L/e150.log 2>&1
step e170; python3 work/editor/e170.py $HD $W/e170_$M $M > $L/e170.log 2>&1
step e180disk; python3 work/editor/e180.py $HD $W/e180d_$M $M $O/odd2.ovl $O/looks.ovl --disk $S > $L/e180_disk.log 2>&1
step e180all12; python3 work/editor/e180.py $HD $W/e180a_$M $M $O/all12.ovl --quick $S > $L/e180_all12.log 2>&1
step e190; python3 work/editor/e190.py $HD $W/e190_$M $M $S > $L/e190.log 2>&1
step e180quick; python3 work/editor/e180.py $HD $W/e180q_$M $M $O/odd2.ovl $O/stress01.ovl $O/stress05.ovl --quick $S > $L/e180_quick.log 2>&1
echo done > $L/done
