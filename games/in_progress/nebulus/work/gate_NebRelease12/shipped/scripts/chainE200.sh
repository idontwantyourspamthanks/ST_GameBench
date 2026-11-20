#!/bin/bash
while [ ! -f /tmp/nr12/logs/hd.done ]; do sleep 20; done
N=/tmp/nr12/nb; X=/tmp/nr12/x; HD=/tmp/nr12/s/hd/NEBULUS; W=/tmp/nr12/wd; cd $N
export HOME=/tmp/nr12/home PYTHONUNBUFFERED=1 SNAP_EXPECT=0203131402020202 PYTHONPATH=/tmp/nr12/sc
for M in ste megaste st; do
 mv /tmp/nr12/logs/$M/e200.log /tmp/nr12/logs/$M/e200_first_noref.log 2>/dev/null
 REFDIR=$X/r/base8_$M python3 work/editor/e200.py $HD $W/e200b_$M $M --snap $X/snap/v12_$M.sav > /tmp/nr12/logs/$M/e200.log 2>&1
done
echo done > /tmp/nr12/logs/e200.done
